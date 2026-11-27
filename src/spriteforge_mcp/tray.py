"""Thin notification-area control app. Lifecycle always invokes the CLI."""

import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor

from spriteforge_mcp.config import Paths, Settings
from spriteforge_mcp.logging_config import configure_logging
from spriteforge_mcp.runtime import Manager
from spriteforge_mcp.security import local_token, singleton
from spriteforge_mcp.updater import REPOSITORY, check_updates


class TrayController:
    def __init__(self, paths: Paths, settings: Settings):
        self.paths = paths
        self.settings = settings
        self.status = {"state": "stopped"}
        self.update = {
            "message": "Not checked",
            "download_available": False,
            "apply_available": False,
        }
        self.closed = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.icon = None

    def refresh(self) -> None:
        if self.icon:
            self.icon.update_menu()

    def report_error(self) -> None:
        logging.getLogger(__name__).exception("Tray operation failed")
        self.status = {"state": "error"}
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(
                None,
                "Operation failed. See runtime/tray.log in the SpriteForge data folder.",
                "SpriteForge MCP",
                0x10,
            )

    def submit(self, operation) -> None:
        def run():
            try:
                operation()
            except Exception:
                self.report_error()
            finally:
                self.refresh()

        self.executor.submit(run)

    def lifecycle(self, command: str) -> None:
        self.status = {"state": "stopping" if command == "stop" else "starting"}
        self.refresh()
        process = subprocess.run(
            [sys.executable, "-m", "spriteforge_mcp", "--data-root", str(self.paths.root), command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=self.settings.startup_timeout + self.settings.shutdown_timeout + 15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.status = json.loads(process.stdout)

    def check_update(self) -> None:
        self.update = check_updates(prereleases=self.settings.update_prereleases)

    def exit(self, stop_daemon: bool = False) -> None:
        if stop_daemon:
            self.lifecycle("stop")
        self.closed.set()
        if self.icon:
            self.icon.stop()

    def poll(self) -> None:
        while not self.closed.is_set():
            try:
                self.status = Manager(self.paths, self.settings).status()
                self.refresh()
            except Exception:
                self.report_error()
                self.refresh()
                return
            if self.closed.wait(self.settings.tray_poll_seconds):
                return

    def open_path(self, path) -> None:
        os.startfile(str(path))

    def menu(self):
        from pystray import Menu, MenuItem

        return Menu(
            MenuItem(lambda item: f"State: {self.status['state']}", None, enabled=False),
            MenuItem(lambda item: f"PID: {self.status.get('pid', '-')}", None, enabled=False),
            MenuItem(
                lambda item: f"Endpoint: {self.status.get('endpoint', '-')}", None, enabled=False
            ),
            MenuItem(
                lambda item: f"Uptime: {int(self.status.get('uptime_seconds', 0))}s",
                None,
                enabled=False,
            ),
            MenuItem(
                lambda item: f"Jobs: {self.status.get('active_jobs', 0)} active / "
                f"{self.status.get('queued_jobs', 0)} queued (pipeline pending)",
                None,
                enabled=False,
            ),
            MenuItem("Start Daemon", lambda: self.submit(lambda: self.lifecycle("start"))),
            MenuItem("Stop Daemon", lambda: self.submit(lambda: self.lifecycle("stop"))),
            MenuItem("Restart Daemon", lambda: self.submit(lambda: self.lifecycle("restart"))),
            MenuItem("Open Logs", lambda: self.submit(lambda: self.open_path(self.paths.log))),
            MenuItem(
                "Open Data Folder", lambda: self.submit(lambda: self.open_path(self.paths.root))
            ),
            MenuItem(
                "Open Settings",
                lambda: self.submit(lambda: self.open_path(self.paths.settings_file)),
            ),
            MenuItem(
                "Updates",
                Menu(
                    MenuItem(lambda item: self.update["message"][:180], None, enabled=False),
                    MenuItem("Check for Updates", lambda: self.submit(self.check_update)),
                    MenuItem("Release Notes", lambda: webbrowser.open(f"{REPOSITORY}/releases")),
                    MenuItem("Download Update", None, enabled=False),
                    MenuItem("Install and Restart", None, enabled=False),
                    MenuItem(
                        "Update Settings",
                        lambda: self.submit(lambda: self.open_path(self.paths.settings_file)),
                    ),
                ),
            ),
            MenuItem("Exit Tray", lambda: self.exit()),
            MenuItem("Exit and Stop Daemon", lambda: self.submit(lambda: self.exit(True))),
        )


def run_tray(paths: Paths, settings: Settings) -> None:
    from PIL import Image, ImageDraw
    from pystray import Icon

    with singleton("Tray"):
        paths.initialize()
        token = local_token(paths) if paths.secret.exists() else ""
        configure_logging(paths, token, tray=True)
        controller = TrayController(paths, settings)
        image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((4, 4, 27, 27), fill="#52b788")
        icon = Icon("SpriteForge MCP", image, "SpriteForge MCP", controller.menu())
        controller.icon = icon

        def setup(icon):
            icon.visible = True
            threading.Thread(target=controller.poll, daemon=True).start()

            def delayed_check():
                if not controller.closed.wait(5):
                    controller.submit(controller.check_update)

            threading.Thread(target=delayed_check, daemon=True).start()

        try:
            icon.run(setup)
        finally:
            controller.closed.set()
            controller.executor.shutdown(wait=True, cancel_futures=True)
