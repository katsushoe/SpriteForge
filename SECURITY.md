# Security

SpriteForge runs in the logged-in user's Windows session. No Windows Service, elevated task,
administrator privilege, installation, or machine-wide startup registration is introduced.

HTTP binds only to `127.0.0.1`. Host headers are validated, browser Origin requests are rejected,
and MCP/status/control requests require a constant-time-checked bearer token.
The token is encrypted at rest with current-user Windows DPAPI and is never passed in CLI arguments.
Health information is non-secret. Status verifies instance metadata and the process executable,
command line, owner and Windows session. A stale PID does not authorize killing any process.

Request bodies are bounded, managed paths are resolved under the data root, and logs redact bearer
tokens and the runtime token including formatted exceptions. Same-user programs are within the
Windows user trust boundary; DPAPI is not a defense against malicious code running as that user.

Release discovery is fixed to the official GitHub repository. Only explicit compatible Windows
package assets can be classified as packages; source archives are not installers. A matching
SHA-256 manifest is required even to identify a future package as ready for verification.
No package download, extraction, executable replacement or update helper is implemented yet.
Metadata-only releases do not modify installation files or stop the daemon.

Client registration stores only an environment-variable reference. An explicitly invoked auth-shell
passes the DPAPI-decrypted token in its child environment without changing registry/user environment
settings, arguments or output. Other processes running as the same Windows user remain trusted.
Ownership metadata prevents unconfigure from deleting modified or unowned settings. Actual client
configuration changes require an explicit user operation; tests use temporary files.

This is a development build. Desktop client credential provisioning, image import limits, persistent job
recovery, signed update verification, rollback and MSI packaging remain later work.
