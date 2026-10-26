"""Static configuration. Nothing here pins a Hiren's version or checksum:
the ISO URL and checksums are discovered from the official page at runtime."""

from __future__ import annotations

import os
from pathlib import Path

from . import APP_ID

# Official distribution page. The only page the app reads release data from.
OFFICIAL_DOWNLOAD_PAGE = "https://www.hirensbootcd.org/download/"

# Hosts the ISO may be downloaded from (exact host or a subdomain of it).
# Redirects that leave these domains abort the download.
OFFICIAL_DOMAINS = ("hirensbootcd.org",)

# FAT32 is required for UEFI boot on most firmware. Windows' own formatter
# refuses FAT32 above 32 GB, so the boot partition is capped below that.
FAT32_MAX_PARTITION_BYTES = 31 * 1024**3
FAT32_MAX_FILE_BYTES = 4 * 1024**3 - 1

# Reject anything smaller than this regardless of ISO size.
MIN_USB_BYTES = 1 * 1024**3
# Extra room required on the USB beyond the ISO payload (FAT overhead, slack).
USB_HEADROOM_BYTES = 256 * 1024**2
# Refuse "USB" disks above this size: almost certainly an external system/backup
# drive rather than a flash drive, and a wrong pick would be catastrophic.
MAX_USB_BYTES = 2 * 1024**4

USER_AGENT = f"{APP_ID}/1.0 (+Windows; bootable USB creator)"
HTTP_TIMEOUT_S = 30
DOWNLOAD_CHUNK = 1024 * 1024


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    path = Path(base) / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
