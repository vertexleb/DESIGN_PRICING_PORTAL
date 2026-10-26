"""Boot-structure checks: ISO content layout before writing, MBR/PBR after writing."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from . import config
from .errors import InvalidIsoError


@dataclass(frozen=True)
class FileEntry:
    relpath: str  # forward slashes, relative to the volume root
    size: int


@dataclass
class BootLayout:
    uefi_loader: str | None = None
    bios_loader: str | None = None
    bcd_stores: list[str] = field(default_factory=list)
    wim_images: list[str] = field(default_factory=list)
    payload_bytes: int = 0
    file_count: int = 0

    @property
    def supports_uefi(self) -> bool:
        return bool(self.uefi_loader)

    @property
    def supports_bios(self) -> bool:
        return bool(self.bios_loader)


def analyse_layout(entries: list[FileEntry]) -> BootLayout:
    """Validate a WinPE-style tree (Hiren's BootCD PE). Raises InvalidIsoError if it cannot boot."""
    layout = BootLayout()
    too_big = []
    for e in entries:
        low = e.relpath.lower().lstrip("/")
        layout.payload_bytes += e.size
        layout.file_count += 1
        if e.size > config.FAT32_MAX_FILE_BYTES:
            too_big.append(e.relpath)
        if low == "efi/boot/bootx64.efi":
            layout.uefi_loader = e.relpath
        elif low == "bootmgr":
            layout.bios_loader = e.relpath
        elif low in ("boot/bcd", "efi/microsoft/boot/bcd"):
            layout.bcd_stores.append(e.relpath)
        elif low.endswith(".wim"):
            layout.wim_images.append(e.relpath)
    if too_big:
        raise InvalidIsoError(
            "The ISO contains files larger than 4 GB, which FAT32 cannot store: " + ", ".join(too_big)
        )
    missing = []
    if not layout.uefi_loader:
        missing.append("EFI/BOOT/BOOTX64.EFI (UEFI boot loader)")
    if not layout.bcd_stores:
        missing.append("BCD boot configuration")
    if not layout.wim_images:
        missing.append("Windows PE image (.wim)")
    if missing:
        raise InvalidIsoError(
            "The ISO is not a bootable Hiren's BootCD PE image; missing: " + "; ".join(missing)
        )
    return layout


@dataclass(frozen=True)
class MbrPartition:
    active: bool
    type_id: int
    lba_start: int
    sectors: int


def parse_mbr(sector0: bytes) -> tuple[bool, bool, list[MbrPartition]]:
    """Return (signature_ok, boot_code_present, partitions)."""
    if len(sector0) < 512:
        return False, False, []
    signature_ok = sector0[510:512] == b"\x55\xaa"
    boot_code_present = any(sector0[:440])
    parts = []
    for i in range(4):
        raw = sector0[446 + 16 * i: 446 + 16 * (i + 1)]
        status, ptype = raw[0], raw[4]
        lba, count = struct.unpack("<II", raw[8:16])
        if ptype:
            parts.append(MbrPartition(active=status == 0x80, type_id=ptype, lba_start=lba, sectors=count))
    return signature_ok, boot_code_present, parts


def mbr_problems(sector0: bytes) -> list[str]:
    sig, code, parts = parse_mbr(sector0)
    problems = []
    if not sig:
        problems.append("MBR signature missing")
    if len(parts) != 1:
        problems.append(f"expected exactly 1 partition, found {len(parts)}")
    elif not parts[0].active:
        problems.append("partition is not marked active")
    elif parts[0].type_id not in (0x0B, 0x0C):
        problems.append(f"partition type 0x{parts[0].type_id:02X} is not FAT32")
    if not code:
        problems.append("MBR boot code missing (legacy BIOS boot)")
    return problems


def pbr_info(volume_head: bytes) -> tuple[bool, str | None]:
    """Return (is_fat32, loader) where loader is 'BOOTMGR', 'NTLDR' or None."""
    is_fat32 = len(volume_head) >= 512 and volume_head[82:90] == b"FAT32   " and volume_head[510:512] == b"\x55\xaa"
    loader = None
    if b"BOOTMGR" in volume_head:
        loader = "BOOTMGR"
    elif b"NTLDR" in volume_head:
        loader = "NTLDR"
    return is_fat32, loader
