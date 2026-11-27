import asyncio
import json
import logging
import socket
import subprocess
import sys
from unittest.mock import Mock

import httpx
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from pydantic import ValidationError

from spriteforge_mcp.config import Paths, Settings
from spriteforge_mcp.logging_config import RedactedFormatter
from spriteforge_mcp.runtime import Manager
from spriteforge_mcp.security import AlreadyRunning, local_token, protect, singleton
from spriteforge_mcp.server import build_http_app, build_mcp_server
from spriteforge_mcp.tray import TrayController
from spriteforge_mcp.updater import classify_release


@pytest.fixture
def paths(tmp_path):
    result = Paths(tmp_path)
    result.initialize()
    return result


@pytest.mark.parametrize("relative", ["../outside", "projects/../../outside"])
def test_managed_paths_reject_traversal(paths, relative):
    with pytest.raises(ValueError):
        paths.managed(relative)


@pytest.mark.parametrize("values", [{"port": 0}, {"host": "0.0.0.0"}, {"tray_poll_seconds": 1}])
def test_settings_reject_invalid_configuration(values):
    with pytest.raises(ValidationError):
        Settings(**values)


def test_dpapi_token_is_persistent_and_not_plaintext(paths):
    token = local_token(paths, create=True)
    assert local_token(paths) == token
    assert token.encode() not in paths.secret.read_bytes()
    assert protect(protect(b"secret"), decrypt=True) == b"secret"


def test_mutex_prevents_duplicate_daemon_and_releases():
    with singleton("TestSingleton"):
        with pytest.raises(AlreadyRunning), singleton("TestSingleton"):
            pytest.fail("Duplicate guard was acquired")
    with singleton("TestSingleton"):
        pass


def test_logs_redact_token_and_bearer_including_exceptions():
    formatter = RedactedFormatter("secret-token")
    record = logging.LogRecord(
        "test", logging.ERROR, "test.py", 1, "secret-token Bearer another-token", (), None
    )
    text = formatter.format(record)
    assert "secret-token" not in text
    assert "another-token" not in text


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(paths):
    settings = Settings(max_request_bytes=1024)
    stop = Mock()
    app = build_http_app(paths, settings, "test-token", stop)
    async with app.app.router.lifespan_context(app.app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8765"
        ) as connection:
            yield connection, stop


@pytest.mark.anyio
async def test_health_is_public_but_control_and_mcp_require_auth(client):
    connection, stop = client
    assert (await connection.get("/health")).status_code == 200
    for route in ("/status", "/mcp", "/control/stop"):
        assert (await connection.post(route)).status_code == 401
    response = await connection.get("/status", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    stop.assert_not_called()


@pytest.mark.anyio
async def test_http_rejects_origin_and_host_and_large_stream(client):
    connection, _ = client
    response = await connection.get("/health", headers={"Origin": "https://example.org"})
    assert response.status_code == 403
    assert (await connection.get("/health", headers={"Host": "example.org"})).status_code == 403
    response = await connection.post(
        "/mcp", headers={"Authorization": "Bearer test-token"}, content=b"x" * 1025
    )
    assert response.status_code == 413


@pytest.mark.anyio
async def test_stop_checks_instance_and_requests_graceful_shutdown(client):
    connection, stop = client
    headers = {"Authorization": "Bearer test-token"}
    assert (await connection.post("/control/stop", headers=headers)).status_code == 409
    identity = (await connection.get("/health")).json()["instance_id"]
    headers["X-SpriteForge-Instance"] = identity
    assert (await connection.post("/control/stop", headers=headers)).status_code == 200
    stop.assert_called_once()


def test_metadata_only_release_does_not_touch_files_or_stop_daemon(paths):
    before = set(paths.root.rglob("*"))
    info = classify_release({"tag_name": "0.0.1", "assets": [], "body": "Test release"})
    assert info.classification == "metadata_only"
    assert not info.download_available and not info.apply_available
    assert "does not contain an installable package" in info.message
    assert set(paths.root.rglob("*")) == before


def test_source_archives_are_not_installable():
    info = classify_release(
        {"tag_name": "0.0.1", "assets": [], "zipball_url": "https://api.github.com/source.zip"}
    )
    assert info.package_name is None


@pytest.mark.parametrize("trusted", [True, False])
def test_release_requires_official_package_and_manifest(trusted):
    prefix = "https://github.com/katsushoe/SpriteForge/releases/download/0.0.2/"
    if not trusted:
        prefix = "https://malicious.example/"
    name = "SpriteForge-0.0.2-windows-x64.zip"
    info = classify_release(
        {
            "tag_name": "0.0.2",
            "assets": [
                {"name": name, "browser_download_url": prefix + name},
                {"name": "SHA256SUMS.txt", "browser_download_url": prefix + "SHA256SUMS.txt"},
            ],
        }
    )
    assert info.classification == ("package_available" if trusted else "metadata_only")
    assert not info.apply_available


def test_tray_exit_leaves_daemon_running(paths, monkeypatch):
    controller = TrayController(paths, Settings())
    lifecycle = Mock()
    monkeypatch.setattr(controller, "lifecycle", lifecycle)
    try:
        controller.exit()
        lifecycle.assert_not_called()
        assert controller.closed.is_set()
    finally:
        controller.executor.shutdown()


def test_tray_explicit_exit_and_stop_uses_lifecycle(paths, monkeypatch):
    controller = TrayController(paths, Settings())
    lifecycle = Mock()
    monkeypatch.setattr(controller, "lifecycle", lifecycle)
    try:
        controller.exit(True)
        lifecycle.assert_called_once_with("stop")
    finally:
        controller.executor.shutdown()


def test_tray_update_actions_are_in_submenu(paths):
    controller = TrayController(paths, Settings())
    try:
        items = list(controller.menu().items)
        update = next(item for item in items if item.text == "Updates")
        assert {item.text for item in update.submenu.items} >= {
            "Check for Updates",
            "Download Update",
            "Install and Restart",
            "Update Settings",
        }
        assert not any(item.text == "Download Update" for item in items)
    finally:
        controller.executor.shutdown()


def test_shared_registry_excludes_lifecycle():
    async def inspect():
        tools = await build_mcp_server().list_tools()
        assert [tool.name for tool in tools] == ["get_version"]
        assert tools[0].annotations.readOnlyHint is True

    asyncio.run(inspect())


def test_stdio_is_protocol_only_and_does_not_start_http(paths):
    async def connect():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "spriteforge_mcp",
                "--data-root",
                str(paths.root),
                "stdio",
            ],
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool("get_version", {})
                assert [tool.name for tool in tools.tools] == ["get_version"]
                assert result.structuredContent["name"] == "SpriteForge MCP"
        assert not paths.metadata.exists()

    asyncio.run(connect())


def test_background_lifecycle_two_clients_restart_and_stale_pid(paths):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    paths.settings_file.write_text(f"port = {port}\nstartup_timeout = 120\n", encoding="utf-8")
    settings = paths.settings()
    manager = Manager(paths, settings)
    paths.metadata.write_text(json.dumps({"pid": 1, "instance_id": "stale"}), encoding="utf-8")
    started = manager.start()
    try:
        assert started["state"] == "running"
        assert manager.start()["pid"] == started["pid"]
        token = local_token(paths)

        async def one_client():
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"},
                timeout=httpx.Timeout(30, connect=5),
                trust_env=False,
            ) as http_client:
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp",
                    http_client=http_client,
                ) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        assert (await session.list_tools()).tools[0].name == "get_version"
                        result = await session.call_tool("get_version", {})
                        assert result.structuredContent["version"] == "0.0.0.0"
                        bad = await session.call_tool("missing_tool", {})
                        assert bad.isError

        async def two_clients():
            await asyncio.gather(one_client(), one_client())

        asyncio.run(two_clients())
        # A separate CLI invocation does not own the already-running daemon.
        command = subprocess.run(
            [
                sys.executable,
                "-m",
                "spriteforge_mcp",
                "--data-root",
                str(paths.root),
                "status",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert command.returncode == 0, command.stderr
        assert json.loads(command.stdout)["pid"] == started["pid"]
        restarted = manager.restart()
        assert restarted["instance_id"] != started["instance_id"]
        assert not httpx.get(f"http://127.0.0.1:{port}/status", trust_env=False).is_success
    finally:
        manager.stop()
    assert manager.status()["state"] == "stopped"
    assert not paths.metadata.exists()
