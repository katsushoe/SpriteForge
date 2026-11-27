# MCP connection

English | [日本語](MCP_SETUP.ja.md)

## Runtime contract

The user starts the daemon through the CLI or tray. Claude Code and Codex only connect to
`http://127.0.0.1:8765/mcp` using Streamable HTTP. Do not register a command or STDIO child process
for normal use. Closing an AI client must not stop the daemon.

The HTTP endpoint requires a local bearer token stored with Windows DPAPI. `/health` is public;
`/status`, `/mcp` and `/control/stop` require authentication. No lifecycle tool is exposed over MCP.
The initial shared HTTP/STDIO registry contains the read-only `get_version` tool only.

## Client readiness

No actual Claude Code or Codex settings have been changed by this implementation.
Automatic `configure`/`unconfigure`, protected client credential provisioning, and real-client
connection verification are pending. An endpoint-only configuration without a bearer token will
fail with HTTP 401. Do not copy the encrypted token file into client settings or publish a token.

SDK integration tests exercise initialize, tool discovery, structured version output and invalid-tool
errors using two concurrent clients. This is not a claim of validation inside either AI application.

## Troubleshooting

Use `uv run spriteforge status`, `uv run spriteforge doctor` and `uv run spriteforge logs` in
PowerShell from the repository. `running` reports the verified daemon PID and endpoint.
`stopped` means start the daemon explicitly. `error` means inspect logs/configuration; the CLI
does not kill the process occupying the port.

For protocol diagnostics only, manually run `uv run spriteforge stdio`. This does not start or
stop HTTP. Its stdout is reserved for MCP protocol messages; logs go to stderr and the log file.
