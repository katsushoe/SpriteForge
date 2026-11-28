"""User-facing lifecycle CLI. Imported by neither AI client's launch configuration."""

import argparse
import json
import logging
import socket
import sys
import time
from pathlib import Path

from spriteforge_mcp import __version__
from spriteforge_mcp.config import Paths


def emit(value) -> None:
    print(json.dumps(value, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="spriteforge")
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument(
        "--data-root", type=Path, help="Override managed storage for tests/development"
    )
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("start", "stop", "restart", "status", "serve", "stdio", "doctor", "tray"):
        commands.add_parser(name)
    logs = commands.add_parser("logs")
    logs.add_argument("--lines", type=int, default=50, choices=range(1, 1001), metavar="1..1000")
    logs.add_argument("--follow", action="store_true")
    update = commands.add_parser("update")
    update.add_argument("action", choices=["check", "status", "configure", "download", "apply"])
    for operation in ("configure", "unconfigure"):
        client = commands.add_parser(operation)
        client.add_argument("client", choices=["codex", "claude"])
        client.add_argument("--config-path", type=Path, help="Explicit client configuration file")
        client.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    commands.add_parser("auth-shell", help="Open a shell with the DPAPI token in its environment")
    return result


def doctor(paths: Paths, settings) -> dict:
    from spriteforge_mcp.runtime import Manager
    from spriteforge_mcp.security import local_token

    token_ready = False
    if paths.secret.exists():
        token_ready = bool(local_token(paths))
    with socket.socket() as probe:
        probe.settimeout(2)
        port_in_use = probe.connect_ex(("127.0.0.1", settings.port)) == 0
    status = Manager(paths, settings).status()
    return {
        "data_root": str(paths.root),
        "storage_exists": paths.root.is_dir(),
        "settings_file": str(paths.settings_file),
        "config_valid": True,
        "token_ready": token_ready,
        "port_in_use": port_in_use,
        "daemon": status,
        "database": "not_implemented",
        "provider": "not_implemented",
    }


def show_logs(paths: Paths, count: int, follow: bool) -> None:
    from collections import deque

    if not paths.log.exists():
        emit({"state": "no_logs"})
        return
    with paths.log.open(encoding="utf-8", errors="replace") as stream:
        for line in deque(stream, maxlen=count):
            print(line.rstrip())
        while follow:
            line = stream.readline()
            if line:
                print(line.rstrip(), flush=True)
            else:
                time.sleep(0.2)


def execute(args, paths: Paths) -> int:
    settings = paths.settings()
    command = args.command
    if command in {"start", "stop", "restart", "status"}:
        from spriteforge_mcp.runtime import Manager

        status = getattr(Manager(paths, settings), command)()
        emit(status)
        return 1 if status["state"] == "error" else 0
    if command == "serve":
        from spriteforge_mcp.server import run_http_daemon

        run_http_daemon(paths, settings)
    elif command == "stdio":
        from spriteforge_mcp.server import run_stdio

        run_stdio(paths)
    elif command == "logs":
        show_logs(paths, args.lines, args.follow)
    elif command == "doctor":
        emit(doctor(paths, settings))
    elif command == "tray":
        from spriteforge_mcp.tray import run_tray

        run_tray(paths, settings)
    elif command in {"configure", "unconfigure"}:
        from spriteforge_mcp.clients import configure

        emit(
            configure(
                paths,
                settings,
                args.client,
                config_path=args.config_path,
                remove=command == "unconfigure",
                dry_run=args.dry_run,
            )
        )
    elif command == "auth-shell":
        from spriteforge_mcp.clients import authenticated_shell

        return authenticated_shell(paths)
    elif command == "update":
        from spriteforge_mcp.updater import check_updates

        if args.action == "check":
            emit(check_updates(prereleases=settings.update_prereleases))
        elif args.action == "status":
            emit({"state": "not_staged", "apply_available": False})
        elif args.action == "configure":
            emit(
                {
                    "settings_file": str(paths.settings_file),
                    "update_prereleases": settings.update_prereleases,
                }
            )
        else:
            raise ValueError("Secure update download/application is not implemented yet")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    paths = None
    try:
        paths = Paths(args.data_root)
        return execute(args, paths)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        from spriteforge_mcp.logging_config import configure_logging
        from spriteforge_mcp.security import local_token

        try:
            if paths and not getattr(args, "dry_run", False):
                token = local_token(paths) if paths.secret.exists() else ""
                configure_logging(paths, token)
            logging.getLogger(__name__).exception("CLI command failed")
        except Exception:
            print("SpriteForge could not write diagnostic logs", file=sys.stderr)
        # Never echo arbitrary exception text (paths, request credentials, or secrets).
        print(
            json.dumps(
                {"error": type(error).__name__, "message": "Command failed; inspect runtime logs"}
            ),
            file=sys.stderr,
        )
        return 1
