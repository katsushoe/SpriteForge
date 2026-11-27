"""CLI-owned background lifecycle. Never terminate an arbitrary PID."""

import json
import logging
import subprocess
import sys
import time

import httpx

from spriteforge_mcp.config import Paths, Settings
from spriteforge_mcp.identity import spawned_by, verify_daemon
from spriteforge_mcp.security import AlreadyRunning, local_token, singleton


class Manager:
    _children: dict[str, subprocess.Popen] = {}

    def __init__(self, paths: Paths, settings: Settings):
        self.paths = paths
        self.settings = settings
        self.base = f"http://127.0.0.1:{settings.port}"

    def status(self) -> dict:
        try:
            with httpx.Client(timeout=httpx.Timeout(3, connect=5), trust_env=False) as client:
                response = client.get(f"{self.base}/health")
                response.raise_for_status()
                health = response.json()
        except httpx.ConnectError:
            return {"state": "stopped"}
        except (httpx.HTTPError, ValueError) as error:
            return {"state": "error", "error": f"Health check failed: {type(error).__name__}"}
        try:
            metadata = json.loads(self.paths.metadata.read_text(encoding="utf-8"))
            if health.get("name") != "SpriteForge MCP" or not all(
                health.get(key) == metadata[key] for key in ("instance_id", "pid", "endpoint")
            ):
                raise ValueError("Daemon identity does not match runtime metadata")
            token = local_token(self.paths)
            with httpx.Client(timeout=2, trust_env=False) as client:
                response = client.get(
                    f"{self.base}/status",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                result = response.json()
            if result.get("instance_id") != metadata["instance_id"]:
                raise ValueError("Daemon instance changed during status request")
            verify_daemon(result["pid"], self.paths.root)
            return result
        except (OSError, ValueError, KeyError, httpx.HTTPError) as error:
            logging.getLogger(__name__).warning(
                "Daemon identity check failed: %s", type(error).__name__
            )
            return {"state": "error", "error": "Cannot authenticate the SpriteForge instance"}

    def start(self) -> dict:
        with singleton("Start"):
            status = self.status()
            if status["state"] == "running":
                return {**status, "already_running": True}
            if status["state"] == "error":
                raise RuntimeError(status["error"])
            self.paths.initialize()
            local_token(self.paths, create=True)
            with self.paths.log.open("ab") as log:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "spriteforge_mcp",
                        "--data-root",
                        str(self.paths.root),
                        "serve",
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True,
                )
            deadline = time.monotonic() + self.settings.startup_timeout
            while time.monotonic() < deadline:
                status = self.status()
                if status["state"] == "running" and spawned_by(status["pid"], child.pid):
                    self._children[status["instance_id"]] = child
                    return status
                if child.poll() is not None:
                    raise RuntimeError("Daemon exited during startup; inspect spriteforge logs")
                time.sleep(0.2)
            raise RuntimeError("Startup timed out; inspect status/logs before retrying")

    def stop(self) -> dict:
        status = self.status()
        if status["state"] == "stopped":
            return status
        if status["state"] != "running":
            raise RuntimeError(status["error"])
        token = local_token(self.paths)
        with httpx.Client(timeout=3, trust_env=False) as client:
            response = client.post(
                f"{self.base}/control/stop",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-SpriteForge-Instance": status["instance_id"],
                },
            )
            response.raise_for_status()
        deadline = time.monotonic() + self.settings.shutdown_timeout
        while time.monotonic() < deadline:
            current = self.status()
            if current["state"] == "stopped":
                # Confirm the daemon has released its singleton, not merely closed its socket.
                try:
                    with singleton("Daemon"):
                        child = self._children.pop(status["instance_id"], None)
                        if child:
                            child.wait(timeout=self.settings.shutdown_timeout)
                        return current
                except AlreadyRunning:
                    pass
            time.sleep(0.2)
        raise RuntimeError("Graceful shutdown timed out; no process was force-killed")

    def restart(self) -> dict:
        self.stop()
        return self.start()
