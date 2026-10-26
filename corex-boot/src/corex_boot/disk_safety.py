"""Target-disk revalidation. Called immediately before any destructive step."""

from __future__ import annotations

import logging

from . import config
from .errors import DeviceDisconnectedError, DiskSafetyError, InsufficientCapacityError
from .usb_detect import DiskSnapshot, UsbDisk, format_size, rejection_reasons

log = logging.getLogger(__name__)


def revalidate(selected: UsbDisk, snapshot: DiskSnapshot) -> UsbDisk:
    """Confirm the user's selected disk is still present, unchanged and safe.

    Returns the fresh record. Never substitutes a different disk: any doubt raises."""
    at_number = [d for d in snapshot.disks if d.number == selected.number]
    by_id = [d for d in snapshot.disks if selected.unique_id and d.unique_id == selected.unique_id]

    if not at_number and not by_id:
        raise DeviceDisconnectedError(
            f"The selected USB drive ({selected.friendly_name}) is no longer connected. "
            "Nothing was written. Reconnect it, press Refresh and select it again."
        )
    if len(at_number) > 1 or len(by_id) > 1:
        raise DiskSafetyError(
            "The selected USB drive cannot be identified unambiguously. Nothing was written. "
            "Disconnect other USB drives, press Refresh and try again."
        )
    current = at_number[0] if at_number else None
    if current is None or not current.same_device(selected):
        log.warning("Disk identity changed: selected=%r current=%r by_id=%r", selected, current, by_id)
        raise DiskSafetyError(
            "The disk at the selected position is no longer the drive you chose "
            "(it was unplugged or replaced). Nothing was written. Press Refresh and select the drive again."
        )
    reasons = rejection_reasons(current, snapshot)
    if reasons:
        raise DiskSafetyError(
            "The selected disk is not a safe target: " + "; ".join(reasons) + ". Nothing was written."
        )
    return current


def usable_bytes(disk: UsbDisk) -> int:
    # 1 MiB partition alignment at the start of the disk.
    return min(disk.size - 1024 * 1024, config.FAT32_MAX_PARTITION_BYTES)


def check_capacity(disk: UsbDisk, payload_bytes: int) -> None:
    required = payload_bytes + config.USB_HEADROOM_BYTES
    if usable_bytes(disk) < required:
        raise InsufficientCapacityError(
            f"The USB drive is too small: {format_size(disk.size)} available, "
            f"at least {format_size(required)} needed. Use a larger USB drive (8 GB or more recommended)."
        )
