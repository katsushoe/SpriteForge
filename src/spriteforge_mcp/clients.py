"""HTTP-only client registration; credentials stay in DPAPI and child environments."""

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import MutableMapping
from pathlib import Path

import tomlkit

from spriteforge_mcp.config import Paths, Settings, atomic_write
from spriteforge_mcp.security import local_token, singleton

SERVER_NAME = "spriteforge-mcp"
TOKEN_VARIABLE = "SPRITEFORGE_MCP_TOKEN"


def client_path(client: str) -> Path:
    if client == "codex":
        return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    if client == "claude":
        return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home()))) / ".claude.json"
    raise ValueError("Supported clients: codex, claude")


def registration(client: str, settings: Settings) -> dict:
    endpoint = f"http://127.0.0.1:{settings.port}/mcp"
    if client == "codex":
        return {
            "url": endpoint,
            "bearer_token_env_var": TOKEN_VARIABLE,
            "enabled": True,
            "tool_timeout_sec": 300,
        }
    if client == "claude":
        return {
            "type": "http",
            "url": endpoint,
            "headers": {"Authorization": f"Bearer ${{{TOKEN_VARIABLE}}}"},
        }
    raise ValueError("Supported clients: codex, claude")


def read_bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def decode(client: str, raw: bytes | None):
    text = raw.decode("utf-8-sig") if raw else ""
    if client == "codex":
        return tomlkit.parse(text)
    value = json.loads(text) if text else {}
    if not isinstance(value, dict):
        raise ValueError("Claude configuration must be a JSON object")
    return value


def encode(client: str, document) -> bytes:
    if client == "codex":
        return tomlkit.dumps(document).encode("utf-8")
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def configure(
    paths: Paths,
    settings: Settings,
    client: str,
    *,
    config_path: Path | None = None,
    remove: bool = False,
    dry_run: bool = False,
) -> dict:
    target = (config_path or client_path(client)).resolve()
    entry = registration(client, settings)
    if not remove and not shutil.which(f"{client}.exe"):
        raise FileNotFoundError(f"{client} is not installed or not on PATH")
    state_file = paths.root / "config" / "client-registrations.json"
    key = hashlib.sha256(f"{client}:{str(target).casefold()}".encode()).hexdigest()
    group_name = "mcp_servers" if client == "codex" else "mcpServers"
    with singleton("ClientConfiguration"):
        original = read_bytes(target)
        original_state = read_bytes(state_file)
        state = json.loads(original_state) if original_state else {}
        document = decode(client, original)
        group = document.get(group_name, {})
        if not isinstance(group, MutableMapping):
            raise ValueError("MCP configuration section must be a table/object")
        existing = group.get(SERVER_NAME)
        recorded = state.get(key)
        if existing is not None and existing != entry and existing != recorded:
            raise ValueError("Existing SpriteForge entry was not created by this installation")
        if remove and existing is not None and existing != recorded:
            raise ValueError("Refusing to remove an entry without matching ownership metadata")
        if remove:
            if SERVER_NAME in group:
                del group[SERVER_NAME]
            state.pop(key, None)
        else:
            if group_name not in document:
                document[group_name] = {}
            document[group_name][SERVER_NAME] = entry
            state[key] = entry
        result = {
            "client": client,
            "config_path": str(target),
            "state": "removed" if remove else "configured",
            "dry_run": dry_run,
            "entry": None if remove else entry,
            "token_environment_variable": TOKEN_VARIABLE,
        }
        if dry_run:
            return result
        updated = encode(client, document)
        if read_bytes(target) != original or read_bytes(state_file) != original_state:
            raise RuntimeError(
                "Configuration changed concurrently; retry after other writes finish"
            )
        if original is None and remove:
            if original_state is not None:
                atomic_write(state_file, json.dumps(state, indent=2).encode("utf-8"))
            return result
        config_changed = original != updated
        if config_changed:
            atomic_write(target, updated)
        try:
            atomic_write(state_file, json.dumps(state, indent=2).encode("utf-8"))
        except Exception:
            if config_changed:
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, original)
            raise
        return result


def authenticated_shell(paths: Paths) -> int:
    """Open an explicitly requested shell with a process-local token; never start the daemon."""
    token = local_token(paths)
    environment = os.environ.copy()
    environment[TOKEN_VARIABLE] = token
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    if not executable.is_file():
        raise FileNotFoundError("Windows PowerShell is unavailable")
    # The token appears only in the child environment, never its arguments or output.
    return subprocess.run(
        [str(executable), "-NoLogo", "-NoProfile"], env=environment, check=False
    ).returncode
