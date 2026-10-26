"""USB disk enumeration via Windows Storage cmdlets (Get-Disk / Get-Partition).

Parsing and classification are pure functions so they can be tested off-Windows."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from . import config
from .powershell import run_script

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class UsbDisk:
    number: int
    friendly_name: str
    serial_number: str
    unique_id: str
    size: int
    bus_type: str
    is_boot: bool = False
    is_system: bool = False
    is_offline: bool = False
    is_read_only: bool = False
    partition_style: str = ""
    location: str = ""
    drive_letters: tuple[str, ...] = ()

    @property
    def physical_path(self) -> str:
        return rf"\\.\PhysicalDrive{self.number}"

    @property
    def disk_id(self) -> str:
        """Short identifier shown to the user."""
        return f"Disk {self.number} ({self.physical_path})"

    def same_device(self, other: "UsbDisk") -> bool:
        """True only if every identifying attribute matches."""
        return (
            self.number == other.number
            and self.unique_id == other.unique_id
            and self.size == other.size
            and self.serial_number == other.serial_number
            and self.friendly_name == other.friendly_name
        )

    def describe(self) -> str:
        letters = ", ".join(f"{l}:" for l in self.drive_letters) or "no drive letter"
        return f"{self.friendly_name} - {format_size(self.size)} - {letters} - {self.disk_id}"


@dataclass(frozen=True)
class DiskSnapshot:
    system_drive: str
    page_file_drives: tuple[str, ...]
    disks: tuple[UsbDisk, ...]


@dataclass
class Classification:
    eligible: list[UsbDisk] = field(default_factory=list)
    rejected: list[tuple[UsbDisk, list[str]]] = field(default_factory=list)


def format_size(num_bytes: int) -> str:
    """Decimal units, matching the capacity printed on USB sticks."""
    value = float(num_bytes)
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if value < 1000 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "bytes" else f"{value:.1f} {unit}"
        value /= 1000
    return f"{value:.1f} TB"


def _as_list(value: Any) -> list:
    # ConvertTo-Json collapses single-element arrays in some PowerShell versions.
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _letter(value: Any) -> str:
    text = str(value or "").strip().rstrip(":").upper()
    return text if len(text) == 1 and text.isalpha() else ""


def parse_snapshot(data: dict[str, Any]) -> DiskSnapshot:
    disks = []
    for raw in _as_list(data.get("Disks")):
        letters = tuple(sorted({l for l in (_letter(x) for x in _as_list(raw.get("DriveLetters"))) if l}))
        disks.append(
            UsbDisk(
                number=int(raw["Number"]),
                friendly_name=str(raw.get("FriendlyName") or "Unknown device").strip(),
                serial_number=str(raw.get("SerialNumber") or "").strip(),
                unique_id=str(raw.get("UniqueId") or "").strip(),
                size=int(raw.get("Size") or 0),
                bus_type=str(raw.get("BusType") or "").strip(),
                is_boot=bool(raw.get("IsBoot")),
                is_system=bool(raw.get("IsSystem")),
                is_offline=bool(raw.get("IsOffline")),
                is_read_only=bool(raw.get("IsReadOnly")),
                partition_style=str(raw.get("PartitionStyle") or ""),
                location=str(raw.get("Location") or ""),
                drive_letters=letters,
            )
        )
    page_files = tuple(sorted({l for l in (_letter(x) for x in _as_list(data.get("PageFileDrives"))) if l}))
    return DiskSnapshot(
        system_drive=_letter(data.get("SystemDrive")) or "C",
        page_file_drives=page_files,
        disks=tuple(disks),
    )


def rejection_reasons(disk: UsbDisk, snapshot: DiskSnapshot) -> list[str]:
    """Every reason this disk must never be written. Empty list means eligible."""
    reasons: list[str] = []
    if disk.bus_type.upper() != "USB":
        reasons.append(f"not a USB device (bus type {disk.bus_type or 'unknown'})")
    if disk.is_boot or disk.is_system:
        reasons.append("Windows boots from this disk")
    if snapshot.system_drive in disk.drive_letters:
        reasons.append(f"contains the Windows drive {snapshot.system_drive}:")
    if any(l in snapshot.page_file_drives for l in disk.drive_letters):
        reasons.append("holds the Windows page file")
    if disk.size <= 0:
        reasons.append("no media inserted")
    elif disk.size < config.MIN_USB_BYTES:
        reasons.append("smaller than 1 GB")
    elif disk.size > config.MAX_USB_BYTES:
        reasons.append("larger than 2 TB (looks like an external hard disk, not a USB flash drive)")
    if disk.is_read_only:
        reasons.append("write-protected")
    if not disk.unique_id:
        reasons.append("Windows reports no unique identifier for it")
    ids = Counter(d.unique_id for d in snapshot.disks if d.unique_id)
    numbers = Counter(d.number for d in snapshot.disks)
    if disk.unique_id and ids[disk.unique_id] > 1:
        reasons.append("ambiguous: another disk reports the same identifier")
    if numbers[disk.number] > 1:
        reasons.append("ambiguous: disk number reported twice")
    return reasons


def classify(snapshot: DiskSnapshot) -> Classification:
    result = Classification()
    for disk in snapshot.disks:
        reasons = rejection_reasons(disk, snapshot)
        if reasons:
            result.rejected.append((disk, reasons))
        else:
            result.eligible.append(disk)
    result.eligible.sort(key=lambda d: d.number)
    return result


def query_snapshot(runner: Callable[..., Any] = run_script) -> DiskSnapshot:
    data = runner("list_disks", timeout=120)
    snapshot = parse_snapshot(data or {})
    log.info(
        "Disk scan: %s",
        "; ".join(f"#{d.number} {d.friendly_name} {d.bus_type} {d.size}B letters={d.drive_letters}" for d in snapshot.disks),
    )
    return snapshot
