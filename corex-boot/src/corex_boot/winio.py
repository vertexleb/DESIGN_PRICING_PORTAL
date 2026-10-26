"""Uncached reads on Windows (FILE_FLAG_NO_BUFFERING) so verification reads data back
from the USB device rather than from the Windows file cache. Falls back to normal
reads elsewhere (tests)."""

from __future__ import annotations

import ctypes
import os
from typing import Iterator

CHUNK = 4 * 1024 * 1024

if os.name == "nt":
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateFileW.restype = wintypes.HANDLE
    _k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    _k32.ReadFile.restype = wintypes.BOOL
    _k32.ReadFile.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
    ]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.VirtualAlloc.restype = ctypes.c_void_p
    _k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
    _k32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]

    _GENERIC_READ = 0x80000000
    _SHARE_RW = 0x1 | 0x2
    _OPEN_EXISTING = 3
    _NO_BUFFERING = 0x20000000
    _SEQUENTIAL = 0x08000000
    _INVALID = ctypes.c_void_p(-1).value

    def iter_uncached(path: str, chunk: int = CHUNK) -> Iterator[bytes]:
        handle = _k32.CreateFileW(str(path), _GENERIC_READ, _SHARE_RW, None, _OPEN_EXISTING,
                                  _NO_BUFFERING | _SEQUENTIAL, None)
        if handle in (None, _INVALID):
            raise ctypes.WinError(ctypes.get_last_error())
        # VirtualAlloc returns page-aligned memory, satisfying NO_BUFFERING alignment.
        buf = _k32.VirtualAlloc(None, chunk, 0x1000 | 0x2000, 0x04)
        if not buf:
            _k32.CloseHandle(handle)
            raise MemoryError("VirtualAlloc failed")
        try:
            while True:
                got = wintypes.DWORD(0)
                if not _k32.ReadFile(handle, buf, chunk, ctypes.byref(got), None):
                    raise ctypes.WinError(ctypes.get_last_error())
                if got.value == 0:
                    break
                yield ctypes.string_at(buf, got.value)
                if got.value < chunk:
                    break
        finally:
            _k32.VirtualFree(buf, 0, 0x8000)
            _k32.CloseHandle(handle)

else:

    def iter_uncached(path: str, chunk: int = CHUNK) -> Iterator[bytes]:
        with open(path, "rb") as fh:
            while block := fh.read(chunk):
                yield block


def read_head(path: str, nbytes: int) -> bytes:
    """Read the first nbytes (rounded up to 4 KiB) of a file or raw device."""
    aligned = (nbytes + 4095) // 4096 * 4096
    for block in iter_uncached(path, aligned):
        return block[:nbytes]
    return b""
