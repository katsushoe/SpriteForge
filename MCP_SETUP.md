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
`configure`/`unconfigure` now support user-scoped HTTP registrations, preserving unrelated settings.
The Codex default is `$CODEX_HOME/config.toml` or `~/.codex/config.toml`; Claude defaults to
`~/.claude.json` (or `.claude.json` in `CLAUDE_CONFIG_DIR`). `--config-path` explicitly overrides it.
Real-client connection verification remains pending. An endpoint-only configuration without a
bearer token fails with HTTP 401. Do not copy the encrypted token file into settings or publish a token.

Registrations reference `SPRITEFORGE_MCP_TOKEN`: Codex uses `bearer_token_env_var`; Claude uses
`Bearer ${SPRITEFORGE_MCP_TOKEN}` in its HTTP header. The actual token is never written to these files.
TOML comments and other client entries are retained; changed or unowned conflicting entries are refused.
Ownership metadata lives in `<data-root>/config/client-registrations.json`. Use the same data root for
registration and removal; removal refuses to delete entries without matching ownership metadata.

For a development CLI session, `spriteforge auth-shell` opens a foreground PowerShell inheriting the
token decrypted from DPAPI. Launch either client manually in that shell. It only provides credentials:
the daemon must already be running and is never started by a client. The token is not stored in the
Windows user environment or included in process arguments. Close the shell to end this credential
session. An already-running desktop client does not inherit a newly opened shell's environment;
desktop provisioning and interactive client validation remain unverified.

Format references: [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp) and
[Claude Code MCP configuration](https://code.claude.com/docs/en/mcp).

SDK integration tests exercise initialize, tool discovery, structured version output and invalid-tool
errors using two concurrent clients. This is not a claim of validation inside either AI application.

## Troubleshooting

Use `uv run spriteforge status`, `uv run spriteforge doctor` and `uv run spriteforge logs` in
PowerShell from the repository. `running` reports the verified daemon PID and endpoint.
`stopped` means start the daemon explicitly. `error` means inspect logs/configuration; the CLI
does not kill the process occupying the port.

For protocol diagnostics only, manually run `uv run spriteforge stdio`. This does not start or
stop HTTP. Its stdout is reserved for MCP protocol messages; logs go to stderr and the log file.
