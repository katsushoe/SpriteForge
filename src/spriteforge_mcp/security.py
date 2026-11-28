"""Session mutex and current-user Windows DPAPI token storage."""

import ctypes
import os
import secrets
from contextlib import contextmanager
from ctypes import wintypes

from spriteforge_mcp.config import Paths, atomic_write


class AlreadyRunning(RuntimeError):
    pass


TEST_NAMESPACE_ENV = "SPRITEFORGE_TEST_MUTEX_NAMESPACE"


def mutex_name(name: str) -> str:
    """Return the session-wide mutex name.

    The guard is intentionally shared across data-root overrides. The test suite alone
    sets TEST_NAMESPACE_ENV so its daemons do not collide with a user's running daemon.
    """
    namespace = os.environ.get(TEST_NAMESPACE_ENV, "")
    if namespace and not namespace.isalnum():
        raise ValueError(f"{TEST_NAMESPACE_ENV} must be alphanumeric")
    prefix = f"Test{namespace}_" if namespace else ""
    return f"Local\\SpriteForgeMCP_{prefix}{name}"


@contextmanager
def singleton(name: str):
    if os.name != "nt":
        raise RuntimeError("SpriteForge lifecycle currently requires Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, mutex_name(name))
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    try:
        if error == 183:
            raise AlreadyRunning(f"SpriteForge {name} is already active in this session")
        yield
    finally:
        kernel.CloseHandle(handle)


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect(data: bytes, *, decrypt: bool = False) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required for local token storage")
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    operation.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    operation.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


def local_token(paths: Paths, *, create: bool = False) -> str:
    if create:
        with singleton("SecretStore"):
            if not paths.secret.exists():
                atomic_write(paths.secret, protect(secrets.token_urlsafe(32).encode("ascii")))
    return protect(paths.secret.read_bytes(), decrypt=True).decode("ascii")
