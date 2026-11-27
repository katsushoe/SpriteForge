"""Persistent configuration and managed storage paths."""

import json
import os
import tempfile
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value).encode("utf-8"))


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    port: int = Field(default=8765, ge=1024, le=65535)
    startup_timeout: float = Field(default=60, ge=1, le=120)
    shutdown_timeout: float = Field(default=20, ge=1, le=120)
    max_request_bytes: int = Field(default=1048576, ge=1024, le=16777216)
    tray_poll_seconds: float = Field(default=3, ge=2, le=5)
    update_prereleases: bool = False


class Paths:
    def __init__(self, root: Path | None = None):
        if root is None:
            local = os.environ.get("LOCALAPPDATA")
            if not local:
                raise ValueError("LOCALAPPDATA is required; use --data-root for testing")
            root = Path(local) / "SpriteForgeMCP"
        self.root = root.resolve()
        self.runtime = self.root / "runtime"
        self.metadata = self.runtime / "daemon.pid"
        self.log = self.runtime / "daemon.log"
        self.settings_file = self.root / "config" / "settings.toml"
        self.secret = self.root / "secrets" / "local-token.dpapi"

    def initialize(self) -> None:
        for name in ("config", "runtime", "db", "projects", "cache", "output", "secrets"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        if not self.settings_file.exists():
            defaults = (
                "port = 8765\nstartup_timeout = 60\nshutdown_timeout = 20\n"
                "max_request_bytes = 1048576\ntray_poll_seconds = 3\n"
                "update_prereleases = false\n"
            )
            atomic_write(self.settings_file, defaults.encode("utf-8"))

    def settings(self) -> Settings:
        if not self.settings_file.exists():
            return Settings()
        with self.settings_file.open("rb") as stream:
            return Settings.model_validate(tomllib.load(stream))

    def managed(self, relative: str) -> Path:
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Path must be inside the managed data root")
        return path
