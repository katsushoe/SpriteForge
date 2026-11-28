import json
import os
import subprocess
import tomllib
from unittest.mock import Mock

import pytest
import tomlkit

from spriteforge_mcp import clients
from spriteforge_mcp.cli import main
from spriteforge_mcp.config import Paths, Settings


@pytest.fixture
def setup(tmp_path, monkeypatch):
    paths = Paths(tmp_path / "data")
    monkeypatch.setattr(clients.shutil, "which", lambda executable: "installed.exe")
    return paths, tmp_path


def parse(client, target):
    text = target.read_text(encoding="utf-8")
    return tomllib.loads(text) if client == "codex" else json.loads(text)


@pytest.mark.parametrize("client", ["codex", "claude"])
def test_registration_is_http_only_and_has_no_secret_or_process_command(client):
    result = clients.registration(client, Settings(port=12345))
    assert result["url"] == "http://127.0.0.1:12345/mcp"
    assert "command" not in result and "args" not in result
    assert clients.TOKEN_VARIABLE in json.dumps(result)


@pytest.mark.parametrize("client", ["codex", "claude"])
def test_configure_and_unconfigure_are_idempotent_and_keep_other_settings(setup, client):
    paths, root = setup
    target = root / ("config.toml" if client == "codex" else ".claude.json")
    group = "mcp_servers" if client == "codex" else "mcpServers"
    if client == "codex":
        target.write_text(
            '# Keep this comment\nmodel = "test"\n[mcp_servers.other]\nurl = "https://example.org/mcp"\n'
        )
    else:
        target.write_text(
            json.dumps({"theme": "dark", group: {"other": {"url": "https://example.org/mcp"}}})
        )
    expected = parse(client, target)
    first = clients.configure(paths, Settings(), client, config_path=target)
    initial = target.read_bytes()
    clients.configure(paths, Settings(), client, config_path=target)
    assert target.read_bytes() == initial
    assert first["state"] == "configured"
    assert parse(client, target)[group]["other"] == expected[group]["other"]
    if client == "codex":
        assert "# Keep this comment" in target.read_text()
    clients.configure(paths, Settings(), client, config_path=target, remove=True)
    clients.configure(paths, Settings(), client, config_path=target, remove=True)
    assert clients.SERVER_NAME not in parse(client, target)[group]
    assert parse(client, target)[group]["other"] == expected[group]["other"]


@pytest.mark.parametrize("client", ["codex", "claude"])
def test_dry_run_writes_nothing(setup, client):
    paths, root = setup
    before = list(root.rglob("*"))
    result = clients.configure(paths, Settings(), client, config_path=root / "new", dry_run=True)
    assert result["dry_run"]
    assert list(root.rglob("*")) == before


@pytest.mark.parametrize("client", ["codex", "claude"])
def test_existing_unowned_entry_is_preserved(setup, client):
    paths, root = setup
    target = root / "client"
    group = "mcp_servers" if client == "codex" else "mcpServers"
    target.write_bytes(
        clients.encode(client, {group: {clients.SERVER_NAME: {"url": "https://example.org"}}})
    )
    original = target.read_bytes()
    with pytest.raises(ValueError, match="not created"):
        clients.configure(paths, Settings(), client, config_path=target)
    assert target.read_bytes() == original


@pytest.mark.parametrize("client", ["codex", "claude"])
def test_unconfigure_refuses_modified_owned_entry(setup, client):
    paths, root = setup
    target = root / "client"
    clients.configure(paths, Settings(), client, config_path=target)
    document = parse(client, target)
    group = "mcp_servers" if client == "codex" else "mcpServers"
    document[group][clients.SERVER_NAME]["url"] = "https://example.org/changed"
    target.write_bytes(clients.encode(client, document))
    before = target.read_bytes()
    with pytest.raises(ValueError):
        clients.configure(paths, Settings(), client, config_path=target, remove=True)
    assert target.read_bytes() == before


@pytest.mark.parametrize("client", ["codex", "claude"])
def test_owned_entry_can_update_port_without_overwriting_other_servers(setup, client):
    paths, root = setup
    target = root / "client"
    clients.configure(paths, Settings(), client, config_path=target)
    clients.configure(paths, Settings(port=12345), client, config_path=target)
    group = "mcp_servers" if client == "codex" else "mcpServers"
    assert parse(client, target)[group][clients.SERVER_NAME]["url"].endswith(":12345/mcp")


def test_missing_client_fails_before_writing(setup, monkeypatch):
    paths, root = setup
    monkeypatch.setattr(clients.shutil, "which", lambda executable: None)
    with pytest.raises(FileNotFoundError):
        clients.configure(paths, Settings(), "codex", config_path=root / "client")
    assert not paths.root.exists()


@pytest.mark.parametrize("existing", [True, False])
def test_metadata_failure_rolls_back_client_configuration(setup, monkeypatch, existing):
    paths, root = setup
    target = root / "client.toml"
    if existing:
        target.write_text('model = "test"\n')
    original = clients.read_bytes(target)
    real_write = clients.atomic_write

    def fail_state(path, data):
        if path.name == "client-registrations.json":
            raise OSError("Simulated disk write error")
        real_write(path, data)

    monkeypatch.setattr(clients, "atomic_write", fail_state)
    with pytest.raises(OSError):
        clients.configure(paths, Settings(), "codex", config_path=target)
    assert clients.read_bytes(target) == original


def test_malformed_config_is_not_overwritten(setup):
    paths, root = setup
    target = root / "client"
    target.write_text("invalid = [")
    with pytest.raises(tomlkit.exceptions.ParseError):
        clients.configure(paths, Settings(), "codex", config_path=target)
    assert target.read_text() == "invalid = ["


def test_auth_shell_passes_token_only_in_child_environment(setup, monkeypatch):
    paths, _ = setup
    sentinel = "test-only-not-a-real-token"
    monkeypatch.setattr(clients, "local_token", lambda paths: sentinel)
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(clients.subprocess, "run", run)
    before = os.environ.get(clients.TOKEN_VARIABLE)
    assert clients.authenticated_shell(paths) == 0
    args, kwargs = run.call_args
    assert sentinel not in str(args)
    assert kwargs["env"][clients.TOKEN_VARIABLE] == sentinel
    assert os.environ.get(clients.TOKEN_VARIABLE) == before


def test_cli_configure_preview_has_no_side_effects(setup, capsys):
    paths, root = setup
    assert (
        main(
            [
                "--data-root",
                str(paths.root),
                "configure",
                "codex",
                "--dry-run",
                "--config-path",
                str(root / "config.toml"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["dry_run"]
    assert not paths.root.exists()


def test_codex_home_override_is_respected(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    assert clients.client_path("codex") == tmp_path / "config.toml"


def test_unconfigure_missing_file_does_not_create_settings(setup):
    paths, root = setup
    result = clients.configure(
        paths, Settings(), "codex", config_path=root / "missing", remove=True
    )
    assert result["state"] == "removed"
    assert not paths.root.exists()


def test_failed_cli_dry_run_does_not_create_logs_or_settings(setup, monkeypatch, capsys):
    paths, root = setup
    monkeypatch.setattr(clients.shutil, "which", lambda executable: None)
    assert (
        main(
            [
                "--data-root",
                str(paths.root),
                "configure",
                "codex",
                "--dry-run",
                "--config-path",
                str(root / "config.toml"),
            ]
        )
        == 1
    )
    assert not paths.root.exists()
    assert "FileNotFoundError" in capsys.readouterr().err


def test_unconfigure_cleans_metadata_after_config_was_deleted(setup):
    paths, root = setup
    target = root / "client.toml"
    clients.configure(paths, Settings(), "codex", config_path=target)
    target.unlink()
    clients.configure(paths, Settings(), "codex", config_path=target, remove=True)
    assert not target.exists()
    state = json.loads((paths.root / "config/client-registrations.json").read_text())
    assert state == {}
