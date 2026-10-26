"""Real Windows side-effects, bundled so the workflow can be tested with fakes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import admin, config, iso_verify, source, usb_copy, usb_detect
from .downloader import Downloader
from .powershell import run_script
from .usb_detect import UsbDisk
from .winio import read_head


def fat_label(raw: str) -> str:
    label = re.sub(r"[^A-Z0-9_\-]", "_", (raw or "").upper()).strip("_")[:11]
    return label or "HBCD_PE"


@dataclass
class Backend:
    is_admin: Callable[[], bool]
    query_snapshot: Callable[[], usb_detect.DiskSnapshot]
    discover_release: Callable[[], source.IsoRelease]
    make_downloader: Callable[..., Downloader]
    check_iso_structure: Callable[[Path], str]
    verify_checksum: Callable[..., str]
    mount_iso: Callable[[Path], tuple[str, str]]
    dismount_iso: Callable[[Path], None]
    list_tree: Callable[[str], list]
    prepare_disk: Callable[[UsbDisk, str], str]
    copy_tree: Callable[..., dict]
    flush_volume: Callable[[str], None]
    verify_tree: Callable[..., None]
    read_mbr: Callable[[UsbDisk], bytes]
    read_volume_head: Callable[[str], bytes]
    cache_dir: Callable[[], Path]


def _mount(path: Path) -> tuple[str, str]:
    data = run_script("mount_iso", {"ImagePath": str(path)}, timeout=120)
    return f"{data['DriveLetter']}:\\", str(data.get("Label") or "")


def _dismount(path: Path) -> None:
    run_script("dismount_iso", {"ImagePath": str(path)}, timeout=120)


def _prepare(disk: UsbDisk, label: str) -> str:
    data = run_script(
        "prepare_disk",
        {
            "DiskNumber": disk.number,
            "ExpectedUniqueId": disk.unique_id,
            "ExpectedSize": disk.size,
            "ExpectedBusType": "USB",
            "MaxPartitionBytes": config.FAT32_MAX_PARTITION_BYTES,
            "Label": fat_label(label),
        },
        timeout=900,
    )
    return f"{data['DriveLetter']}:\\"


def _flush(root: str) -> None:
    run_script("flush_volume", {"DriveLetter": root[0]}, timeout=300)


def windows_backend() -> Backend:
    return Backend(
        is_admin=admin.is_admin,
        query_snapshot=usb_detect.query_snapshot,
        discover_release=source.discover_release,
        make_downloader=Downloader,
        check_iso_structure=iso_verify.check_iso_structure,
        verify_checksum=iso_verify.verify_checksum,
        mount_iso=_mount,
        dismount_iso=_dismount,
        list_tree=usb_copy.list_tree,
        prepare_disk=_prepare,
        copy_tree=usb_copy.copy_tree,
        flush_volume=_flush,
        verify_tree=usb_copy.verify_tree,
        read_mbr=lambda disk: read_head(disk.physical_path, 512),
        read_volume_head=lambda root: read_head(rf"\\.\{root[0]}:", 64 * 1024),
        cache_dir=config.cache_dir,
    )
