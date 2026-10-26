"""ISO integrity: published-checksum verification and ISO 9660 / UDF structure check."""

from __future__ import annotations

import hashlib
import hmac
import logging
import threading
from pathlib import Path
from typing import Callable

from .errors import CancelledError, ChecksumMismatchError, InvalidIsoError

log = logging.getLogger(__name__)

MIN_ISO_BYTES = 64 * 1024 * 1024  # Hiren's PE is several GB; anything tiny is not it.
SECTOR = 2048


def hash_file(
    path: Path,
    algorithm: str,
    progress: Callable[[int, int], None] | None = None,
    cancel: threading.Event | None = None,
    chunk: int = 4 * 1024 * 1024,
) -> str:
    digest = hashlib.new(algorithm)
    total = Path(path).stat().st_size
    done = 0
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            if cancel is not None and cancel.is_set():
                raise CancelledError()
            digest.update(block)
            done += len(block)
            if progress:
                progress(done, total)
    return digest.hexdigest()


def verify_checksum(path: Path, algorithm: str, expected: str, **kwargs) -> str:
    actual = hash_file(path, algorithm, **kwargs)
    log.info("%s %s: expected %s actual %s", algorithm, path.name, expected.lower(), actual)
    if not hmac.compare_digest(actual, expected.lower()):
        raise ChecksumMismatchError(
            f"The downloaded file does not match the official {algorithm.upper()} checksum. "
            "It was deleted. Press Start to download it again."
        )
    return actual


def check_iso_structure(path: Path, min_size: int = MIN_ISO_BYTES) -> str:
    """Return 'ISO9660' or 'UDF' if the file carries a valid volume descriptor; raise otherwise."""
    path = Path(path)
    size = path.stat().st_size
    if size < min_size:
        raise InvalidIsoError(f"The downloaded file is too small ({size} bytes) to be the Hiren's BootCD PE ISO.")
    if size % SECTOR:
        log.warning("ISO size %d is not a multiple of %d", size, SECTOR)
    kinds = set()
    with open(path, "rb") as fh:
        # Volume descriptors start at sector 16; scan a few.
        for sector in range(16, 32):
            fh.seek(sector * SECTOR)
            desc = fh.read(7)
            if len(desc) < 7:
                break
            ident = desc[1:6]
            if ident == b"CD001":
                kinds.add("ISO9660")
                if desc[0] == 0xFF:  # terminator
                    continue
            elif ident in (b"BEA01", b"NSR02", b"NSR03", b"TEA01"):
                kinds.add("UDF")
    if not kinds:
        raise InvalidIsoError("The downloaded file is not a valid ISO image.")
    return "UDF" if "UDF" in kinds else "ISO9660"
