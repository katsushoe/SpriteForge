"""Verify process executable, CLI arguments, owner and Windows session."""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

import psutil


def session_id(pid: int) -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.ProcessIdToSessionId.restype = wintypes.BOOL
    result = wintypes.DWORD()
    if not kernel.ProcessIdToSessionId(pid, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    return result.value


def verify_daemon(pid: int, root: Path) -> None:
    try:
        process = psutil.Process(pid)
        own = psutil.Process()
        arguments = process.cmdline()
        expected = ["-m", "spriteforge_mcp", "--data-root", str(root), "serve"]
        if Path(process.exe()).resolve() != Path(own.exe()).resolve():
            raise ValueError("Daemon executable does not match the current runtime")
        if arguments[1:] != expected:
            raise ValueError("Daemon command line does not match the managed runtime")
        if process.username() != own.username() or session_id(pid) != session_id(os.getpid()):
            raise ValueError("Daemon owner/session does not match the current user session")
    except psutil.Error as error:
        raise ValueError("Cannot verify the daemon process") from error


def spawned_by(pid: int, launcher_pid: int) -> bool:
    """Windows virtualenv redirectors start a child interpreter with a different PID."""
    if pid == launcher_pid:
        return True
    try:
        return psutil.Process(pid).ppid() == launcher_pid
    except psutil.Error:
        return False
