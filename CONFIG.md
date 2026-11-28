# Configuration

English | [日本語](CONFIG.ja.md)

## Location and precedence

User data defaults to `%LOCALAPPDATA%\SpriteForgeMCP`.
`spriteforge --data-root <absolute-directory> <command>` overrides the data root for development.
Settings are read from `<data-root>\config\settings.toml`, then validated before each command.
Missing files use built-in defaults. Unknown keys and invalid values fail with exit code 1.
Settings changes take effect after daemon restart.

## Settings

```toml
port = 8765
startup_timeout = 60
shutdown_timeout = 20
max_request_bytes = 1048576
tray_poll_seconds = 3
update_prereleases = false
```

| Setting | Default | Allowed values |
| --- | --- | --- |
| `port` | 8765 | 1024–65535 |
| `startup_timeout` | 60 | 1–120 seconds |
| `shutdown_timeout` | 20 | 1–120 seconds |
| `max_request_bytes` | 1048576 | 1024–16777216 bytes |
| `tray_poll_seconds` | 3 | 2–5 seconds |
| `update_prereleases` | false | Boolean |

Binding is always `127.0.0.1`; remote binding is not configurable.
The release repository is fixed to `katsushoe/SpriteForge`.

## Storage

`runtime` contains diagnostic metadata and rotating logs. `secrets/local-token.dpapi` contains
the current-user DPAPI-encrypted bearer token. No token is placed on process command lines.
`db`, `projects`, `cache` and `output` are reserved for later image/job features.
The PID metadata is diagnostic and never authorizes termination by itself.

The session mutex prevents multiple daemons across data-root overrides within the same session.
Stop the existing daemon with its original data root before using another root.
`SPRITEFORGE_TEST_MUTEX_NAMESPACE` is reserved for the test suite, which uses it to isolate
its daemons from a running user daemon. Do not set it for normal use.
