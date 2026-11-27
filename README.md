# SpriteForge MCP

English | [日本語](README.ja.md)

A user-managed Windows 10/11 MCP daemon for pixel-art and sprite-animation workflows.
This initial implementation provides lifecycle commands, authenticated HTTP, explicit diagnostic
STDIO, a notification-area application and official GitHub release metadata checks.
Projects, image generation, persistent jobs and exports are not implemented yet.

## Development

Open PowerShell in the repository on Windows. Install Python 3.11+ and uv, then run:

```powershell
uv sync --locked
uv run spriteforge --help
uv run ruff check src tests
uv run pytest -q
```

`uv.lock` fixes direct and transitive dependencies. Initial synchronization downloads packages from
PyPI. Tests use temporary data roots and an available loopback port.

## Start and stop

Run these commands in the same PowerShell session; administrator rights are not required:

```powershell
uv run spriteforge start
uv run spriteforge status
uv run spriteforge stop
```

Successful start/status output has `state: running`; successful stop has `state: stopped`.
The default MCP endpoint is `http://127.0.0.1:8765/mcp`. Repeated start returns the existing PID.
The daemon survives the initiating CLI process.

## Notification-area application

```powershell
uv run spriteforge tray
```

The Windows notification-area icon offers lifecycle controls and monitoring. `Exit Tray` leaves
the daemon running; `Exit and Stop Daemon` explicitly stops it. All update actions are inside
`Updates`. Downloads and installation remain disabled until verified staging and rollback exist.

## Documentation

- [Configuration](CONFIG.md)
- [Commands](COMMANDS.md)
- [MCP connection](MCP_SETUP.md)
- [Dependencies](PACKAGES.md)
- [Security](SECURITY.md)

No Windows Service or elevated operation is introduced. Claude Code and Codex connect to an
already-running HTTP daemon. Actual client configuration has not been modified or verified.
Do not register a command that launches the daemon from either client.
