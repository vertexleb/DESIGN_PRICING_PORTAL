"""Copies the mounted ISO tree to the USB volume, hashing on the way, then reads every
file back (uncached) and compares hashes."""

from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path
from typing import Callable, Iterable

from .boot_verify import FileEntry
from .errors import CancelledError, UsbWriteError
from .winio import iter_uncached

CHUNK = 4 * 1024 * 1024
Progress = Callable[[int, int], None]


def list_tree(root: str | Path) -> list[FileEntry]:
    root = Path(root)
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            entries.append(FileEntry(full.relative_to(root).as_posix(), full.stat().st_size))
    return entries


def copy_tree(
    src_root: str | Path,
    dst_root: str | Path,
    entries: list[FileEntry],
    progress: Progress | None = None,
    cancel: threading.Event | None = None,
) -> dict[str, str]:
    """Copy entries; return {relpath: sha256 of the source bytes}. OSErrors propagate."""
    src_root, dst_root = Path(src_root), Path(dst_root)
    total = sum(e.size for e in entries) or 1
    done = 0
    hashes: dict[str, str] = {}
    for entry in entries:
        src = src_root / entry.relpath
        dst = dst_root / entry.relpath
        dst.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with open(src, "rb") as fin, open(dst, "wb") as fout:
            while block := fin.read(CHUNK):
                if cancel is not None and cancel.is_set():
                    raise CancelledError()
                digest.update(block)
                fout.write(block)
                done += len(block)
                if progress:
                    progress(done, total)
            fout.flush()
            os.fsync(fout.fileno())
        hashes[entry.relpath] = digest.hexdigest()
    return hashes


def verify_tree(
    dst_root: str | Path,
    entries: list[FileEntry],
    hashes: dict[str, str],
    progress: Progress | None = None,
    cancel: threading.Event | None = None,
    reader: Callable[[str], Iterable[bytes]] = iter_uncached,
) -> None:
    dst_root = Path(dst_root)
    total = sum(e.size for e in entries) or 1
    done = 0
    bad = []
    for entry in entries:
        path = dst_root / entry.relpath
        digest = hashlib.sha256()
        size = 0
        for block in reader(str(path)):
            if cancel is not None and cancel.is_set():
                raise CancelledError()
            digest.update(block)
            size += len(block)
            done += len(block)
            if progress:
                progress(min(done, total), total)
        if size != entry.size or digest.hexdigest() != hashes.get(entry.relpath):
            bad.append(entry.relpath)
    if bad:
        shown = ", ".join(bad[:5]) + (" ..." if len(bad) > 5 else "")
        raise UsbWriteError(
            f"{len(bad)} file(s) on the USB drive do not match the ISO ({shown}). "
            "The USB drive may be faulty. Try again or use a different USB drive."
        )

