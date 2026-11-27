"""Shared MCP registry and authenticated loopback HTTP host."""

import hmac
import os
import secrets
import time
from contextlib import asynccontextmanager

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from spriteforge_mcp import __version__
from spriteforge_mcp.config import Paths, Settings, write_json
from spriteforge_mcp.logging_config import configure_logging
from spriteforge_mcp.security import local_token, singleton


class Version(BaseModel):
    name: str = "SpriteForge MCP"
    version: str = __version__


def build_mcp_server() -> FastMCP:
    server = FastMCP("SpriteForge MCP", stateless_http=True, json_response=True)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
    def get_version() -> Version:
        """Return the running SpriteForge MCP product version."""
        return Version()

    return server


class HttpBoundary:
    def __init__(self, app, token: str, settings: Settings):
        self.app = app
        self.token = token
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        allowed_hosts = {f"127.0.0.1:{self.settings.port}".encode(), b"127.0.0.1"}
        if headers.get(b"host") not in allowed_hosts or b"origin" in headers:
            await JSONResponse({"error": "Host or Origin rejected"}, 403)(scope, receive, send)
            return
        if scope["path"] != "/health":
            supplied = headers.get(b"authorization", b"")
            expected = f"Bearer {self.token}".encode("ascii")
            if not hmac.compare_digest(supplied, expected):
                await JSONResponse({"error": "Authentication required"}, 401)(scope, receive, send)
                return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.settings.max_request_bytes:
                await JSONResponse({"error": "Request too large"}, 413)(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def build_http_app(paths: Paths, settings: Settings, token: str, shutdown):
    server = build_mcp_server()
    mcp_app = server.streamable_http_app()
    instance_id = secrets.token_hex(16)
    started = time.time()
    identity = {
        "name": "SpriteForge MCP",
        "version": __version__,
        "pid": os.getpid(),
        "instance_id": instance_id,
        "started_at": started,
        "endpoint": f"http://127.0.0.1:{settings.port}/mcp",
    }

    async def health(request: Request):
        return JSONResponse({**identity, "state": "running"})

    async def status(request: Request):
        return JSONResponse(
            {
                **identity,
                "state": "running",
                "uptime_seconds": time.time() - started,
                "active_jobs": 0,
                "queued_jobs": 0,
                "jobs_available": False,
            }
        )

    async def stop(request: Request):
        if request.headers.get("x-spriteforge-instance") != instance_id:
            return JSONResponse({"error": "Daemon instance changed"}, 409)
        shutdown()
        return JSONResponse({"state": "stopping", "instance_id": instance_id})

    @asynccontextmanager
    async def lifespan(app):
        async with server.session_manager.run():
            write_json(paths.metadata, identity)
            try:
                yield
            finally:
                paths.metadata.unlink(missing_ok=True)

    app = Starlette(
        routes=[
            Route("/health", health),
            Route("/status", status),
            Route("/control/stop", stop, methods=["POST"]),
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )
    return HttpBoundary(app, token, settings)


def run_http_daemon(paths: Paths, settings: Settings) -> None:
    with singleton("Daemon"):
        paths.initialize()
        token = local_token(paths, create=True)
        configure_logging(paths, token)
        config = uvicorn.Config(
            "",
            host="127.0.0.1",
            port=settings.port,
            log_config=None,
            access_log=False,
            timeout_graceful_shutdown=settings.shutdown_timeout,
        )
        server = uvicorn.Server(config)

        def shutdown():
            server.should_exit = True

        config.app = build_http_app(paths, settings, token, shutdown)
        server.run()


def run_stdio(paths: Paths) -> None:
    paths.initialize()
    configure_logging(paths)
    build_mcp_server().run(transport="stdio")
