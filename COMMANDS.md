# Commands

English | [日本語](COMMANDS.ja.md)

Run commands in PowerShell from the repository after `uv sync --locked`.
Prefix every command with `uv run` when using the source checkout.
`--data-root <path>` must precede the subcommand.

| Command | Behavior |
| --- | --- |
| `spriteforge start` | Start a detached user process or report the authenticated existing instance |
| `spriteforge stop` | Request authenticated graceful shutdown; never force-kill by PID |
| `spriteforge restart` | Stop, wait for mutex release, then start |
| `spriteforge status` | Return stopped/running/error and verified runtime information |
| `spriteforge serve` | Run HTTP in the foreground for development |
| `spriteforge stdio` | Explicit standalone MCP over STDIO; never controls the HTTP daemon |
| `spriteforge logs [--lines 50] [--follow]` | Read recent daemon logs or follow appended lines |
| `spriteforge doctor` | Inspect settings/storage/token/port; DB and provider report not implemented |
| `spriteforge tray` | Open the Windows notification-area application |
| `spriteforge update check` | Query official releases; stable channel by default |
| `spriteforge update status` | Report no staged update |
| `spriteforge update configure` | Report the settings path and current prerelease setting |
| `spriteforge update download` | Fail explicitly: verified staging is not implemented |
| `spriteforge update apply` | Fail explicitly: safe installation/rollback is not implemented |
| `spriteforge --version` | Show the initial development version `0.0.0.0` |
| `spriteforge configure codex\|claude [--dry-run] [--config-path <file>]` | Add an HTTP-only entry, preserving unrelated settings |
| `spriteforge unconfigure codex\|claude [--dry-run] [--config-path <file>]` | Remove only an unchanged entry owned by this installation |
| `spriteforge auth-shell` | Open an explicitly requested PowerShell with the DPAPI token in that process environment |

Normal command results are JSON on stdout; errors are safe JSON on stderr with exit code 1.
Ctrl+C returns 130. Argument errors return 2. STDIO stdout is reserved for MCP messages.
`logs` prints text and `--version` prints a version string.

Running status includes PID, endpoint, instance ID, uptime, and job counts. Job counts are currently
zero with `jobs_available: false`; they do not imply a functioning job manager.
Repeated start adds `already_running: true` and preserves PID. Missing daemon yields `stopped`.
An occupied, unrecognized or unauthenticated endpoint yields `error`; no unrelated process is killed.

All tray update commands are under `Updates`; source archives and releases without compatible
packages cannot be downloaded/installed.

Client registration requires that client's executable on PATH; removal also works after the client
has been uninstalled. Dry runs write nothing. Conflicting, malformed or modified entries fail without
overwriting them. Config writes are atomic; a metadata-write failure restores the previous config.
The auth shell requires an existing token, never starts the daemon, and does not persist a user-level
environment variable. Exit the shell to discard its environment. Actual client registration is an
explicit user operation, separate from implementing these commands.
