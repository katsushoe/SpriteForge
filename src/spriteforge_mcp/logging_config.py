"""File/stderr logs; formatted exceptions are redacted as well."""

import logging
import re
import sys
from logging.handlers import RotatingFileHandler

from spriteforge_mcp.config import Paths


class RedactedFormatter(logging.Formatter):
    def __init__(self, token: str = ""):
        super().__init__("%(asctime)s [%(levelname)s] %(message)s %(filename)s(%(lineno)d)")
        self.token = token

    def format(self, record: logging.LogRecord) -> str:
        result = super().format(record)
        if self.token:
            result = result.replace(self.token, "(redacted)")
        return re.sub(r"(?i)(bearer\s+)[^\s\"']+", r"\1(redacted)", result)


def configure_logging(paths: Paths, token: str = "", *, tray: bool = False) -> None:
    paths.runtime.mkdir(parents=True, exist_ok=True)
    destination = paths.runtime / "tray.log" if tray else paths.log
    handler = RotatingFileHandler(destination, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    formatter = RedactedFormatter(token)
    handler.setFormatter(formatter)
    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler, stderr], force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)
