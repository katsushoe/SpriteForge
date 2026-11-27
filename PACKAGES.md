# Dependencies

`pyproject.toml` defines direct dependency compatibility bounds; `uv.lock` pins all resolved versions
and distribution hashes. The package source is PyPI. Use `uv sync --locked` for reproducible installs.
Update dependencies explicitly, regenerate the lock, and run lint, lifecycle and protocol tests.

| Package | Purpose |
| --- | --- |
| `mcp` | Official MCP Python SDK, shared Streamable HTTP and STDIO registration |
| `httpx` | Bounded loopback control requests and official release metadata requests |
| `uvicorn` | Loopback ASGI server |
| `pydantic` | Validated configuration and structured tool output |
| `pystray`, `pillow` | Windows notification-area UI and code-generated icon |
| `packaging` | Version parsing and stable/prerelease comparison |
| `psutil` | Process executable, owner and command-line verification |
| `hatchling` | Wheel/sdist build backend |
| `pytest`, `ruff` | Test runner, lint and formatting |

The tray does not import the MCP server or image-generation provider modules. Pillow is used for
the icon only. Real image-generation services and API keys are not configured.

Upstream SDK hosting patterns: [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
Tray API: [official pystray reference](https://pystray.readthedocs.io/en/stable/reference.html).
No claim of a completed dependency vulnerability audit is made by this initial implementation.
