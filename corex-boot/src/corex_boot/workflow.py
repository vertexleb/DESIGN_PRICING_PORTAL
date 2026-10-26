"""End-to-end workflow: discover -> download -> verify ISO -> revalidate disk ->
prepare -> copy -> read-back verify -> boot-structure verify -> clean up."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .backend import Backend
from .boot_verify import analyse_layout, mbr_problems, pbr_info
from .disk_safety import check_capacity, revalidate
from .errors import (
    BootVerificationError,
    CancelledError,
    ChecksumMismatchError,
    CorexError,
    DeviceDisconnectedError,
    DiskSafetyError,
    PermissionDeniedError,
    PowerShellError,
    UsbWriteError,
)
from .usb_detect import UsbDisk, format_size

log = logging.getLogger(__name__)

# Progress bands (percent of the overall bar).
P_DOWNLOAD = (2, 50)
P_HASH = (50, 57)
P_COPY = (60, 88)
P_VERIFY = (88, 98)


class UI(Protocol):
    def stage(self, text: str) -> None: ...
    def progress(self, percent: float) -> None: ...
    def download_status(self, text: str) -> None: ...
    def confirm(self, title: str, text: str) -> bool: ...


@dataclass
class Result:
    iso_verified: bool
    checksum_algorithm: str | None
    version: str | None
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _band(band: tuple[float, float], done: int, total: int | None) -> float:
    lo, hi = band
    if not total:
        return lo
    return lo + (hi - lo) * min(done / total, 1.0)


class Workflow:
    def __init__(self, disk: UsbDisk, ui: UI, backend: Backend, cancel: threading.Event | None = None) -> None:
        self.disk = disk
        self.ui = ui
        self.backend = backend
        self.cancel = cancel or threading.Event()
        self.writing = False  # True once the USB has been erased

    def _check_cancel(self) -> None:
        if self.cancel.is_set():
            raise CancelledError("Cancelled. Nothing was written to the USB drive." if not self.writing else
                                 "Cancelled. The USB drive is incomplete - run Corex Boot again to finish it.")

    def _revalidate(self) -> UsbDisk:
        return revalidate(self.disk, self.backend.query_snapshot())

    def _usb_gone(self) -> bool:
        try:
            snap = self.backend.query_snapshot()
        except CorexError:
            return False
        return not any(d.unique_id == self.disk.unique_id for d in snap.disks)

    def run(self) -> Result:
        b, ui = self.backend, self.ui
        if not b.is_admin():
            raise PermissionDeniedError(
                "Corex Boot needs Administrator rights to write to the USB drive. "
                "Close it, right-click it and choose 'Run as administrator'."
            )
        ui.stage("Checking the selected USB drive...")
        self.disk = self._revalidate()

        # 1. Discover the official release.
        ui.stage("Finding the latest official Hiren's BootCD PE release...")
        ui.progress(1)
        release = b.discover_release()
        best = release.best_checksum
        result = Result(iso_verified=False, checksum_algorithm=best[0] if best else None, version=release.version)
        if not best:
            log.warning("No usable checksum published for %s", release.url)
            if not ui.confirm(
                "Checksum not available",
                "The official Hiren's BootCD website does not currently publish a checksum that Corex Boot "
                "could read, so the download CANNOT be verified as authentic and undamaged.\n\n"
                "Continue with an unverified ISO?",
            ):
                raise CancelledError("Stopped because the ISO could not be verified. Nothing was written.")
            result.warnings.append("The ISO was NOT checksum-verified (no official checksum could be read).")
        self._check_cancel()

        # 2. Download (resumable).
        ui.stage(f"Downloading {release.filename}" + (f" (version {release.version})" if release.version else "") + "...")

        def on_progress(done: int, total: int | None, speed: float) -> None:
            ui.progress(_band(P_DOWNLOAD, done, total))
            text = f"{format_size(done)}" + (f" of {format_size(total)}" if total else "")
            if speed:
                text += f"  -  {format_size(int(speed))}/s"
            ui.download_status(text)

        downloader = b.make_downloader(
            release.url,
            Path(b.cache_dir()) / release.filename,
            progress=on_progress,
            on_total=lambda total: check_capacity(self.disk, total),
            cancel=self.cancel,
        )
        iso_path = downloader.run()
        ui.download_status("complete")
        self._check_cancel()

        # 3. Verify the ISO.
        ui.stage("Verifying the downloaded ISO...")
        try:
            b.check_iso_structure(iso_path)
        except CorexError:
            downloader.discard()
            raise
        if best:
            algo, expected = best
            try:
                b.verify_checksum(
                    iso_path, algo, expected,
                    progress=lambda d, t: ui.progress(_band(P_HASH, d, t)),
                    cancel=self.cancel,
                )
            except ChecksumMismatchError:
                downloader.discard()
                raise
            result.iso_verified = True
            result.checks.append(f"ISO {algo.upper()} matches the checksum published on hirensbootcd.org")
        ui.progress(P_HASH[1])
        self._check_cancel()

        mounted = False
        try:
            ui.stage("Reading the ISO contents...")
            iso_root, iso_label = b.mount_iso(iso_path)
            mounted = True
            entries = b.list_tree(iso_root)
            layout = analyse_layout(entries)
            check_capacity(self.disk, layout.payload_bytes)
            if not layout.supports_bios:
                result.warnings.append("The ISO has no BOOTMGR; the USB will boot on UEFI computers only.")
            self._check_cancel()

            # 4. Last check before anything is written.
            ui.stage("Re-checking the USB drive before erasing...")
            self.disk = self._revalidate()
            ui.stage(f"Preparing USB drive (Disk {self.disk.number}, {self.disk.friendly_name})...")
            ui.progress(58)
            usb_root = self._prepare(iso_label)
            log.info("USB prepared as %s", usb_root)

            # 5. Copy and read back.
            try:
                ui.stage("Writing Hiren's BootCD PE to the USB drive. Do not remove the drive...")
                hashes = b.copy_tree(
                    iso_root, usb_root, entries,
                    progress=lambda d, t: ui.progress(_band(P_COPY, d, t)),
                    cancel=self.cancel,
                )
                b.flush_volume(usb_root)
                ui.stage("Verifying every file on the USB drive...")
                b.verify_tree(
                    usb_root, entries, hashes,
                    progress=lambda d, t: ui.progress(_band(P_VERIFY, d, t)),
                    cancel=self.cancel,
                )
            except OSError as exc:
                log.exception("I/O error while writing USB")
                if self._usb_gone():
                    raise DeviceDisconnectedError(
                        "The USB drive was disconnected while it was being written. "
                        "Reconnect it and run Corex Boot again."
                    ) from exc
                raise UsbWriteError(
                    f"Writing to the USB drive failed: {exc.strerror or exc}. "
                    "Try again, or use a different USB drive."
                ) from exc
            result.checks.append(
                f"All {layout.file_count} files ({format_size(layout.payload_bytes)}) were read back "
                "from the USB drive and match the ISO"
            )

            # 6. Boot structures.
            ui.stage("Checking boot structures...")
            self._verify_boot(usb_root, layout, result)
        finally:
            if mounted:
                try:
                    b.dismount_iso(iso_path)
                except CorexError:
                    log.exception("Could not dismount ISO")

        # 7. Clean up temporary files only after success.
        downloader.discard()
        ui.progress(100)
        ui.stage("Bootable USB Ready")
        return result

    def _prepare(self, label: str) -> str:
        self.writing = True
        try:
            return self.backend.prepare_disk(self.disk, label)
        except PowerShellError as exc:
            if str(exc).startswith("SAFETY:"):
                # The erase script refused before touching the disk.
                self.writing = False
                raise DiskSafetyError(str(exc).removeprefix("SAFETY:").strip()) from exc
            if self._usb_gone():
                raise DeviceDisconnectedError(
                    "The USB drive was disconnected while it was being prepared. Reconnect it and run Corex Boot again."
                ) from exc
            raise UsbWriteError(f"Windows could not prepare the USB drive: {exc}") from exc

    def _verify_boot(self, usb_root: str, layout, result: Result) -> None:
        b = self.backend
        try:
            mbr = b.read_mbr(self.disk)
            head = b.read_volume_head(usb_root)
        except OSError as exc:
            if self._usb_gone():
                raise DeviceDisconnectedError("The USB drive was disconnected during final checks.") from exc
            raise BootVerificationError(f"Could not read the USB boot sectors: {exc}") from exc

        problems = mbr_problems(mbr)
        fatal = [p for p in problems if "boot code" not in p]
        if fatal:
            raise BootVerificationError("The USB partition table is not bootable: " + "; ".join(fatal))
        is_fat32, loader = pbr_info(head)
        if not is_fat32:
            raise BootVerificationError("The USB drive was not formatted as FAT32, which UEFI boot requires.")
        result.checks.append("Partition table: MBR with one active FAT32 partition")
        result.checks.append(f"UEFI boot loader present: {layout.uefi_loader}")

        on_usb = {e.relpath.lower() for e in b.list_tree(usb_root)}
        if layout.uefi_loader.lower() not in on_usb:
            raise BootVerificationError("The UEFI boot loader is missing from the USB drive.")
        if layout.supports_bios:
            if loader == "BOOTMGR" and "boot code" not in " ".join(problems):
                result.checks.append("Legacy BIOS: MBR boot code and BOOTMGR boot sector present")
            else:
                result.warnings.append(
                    "Legacy BIOS boot code could not be confirmed; the USB is expected to boot on UEFI computers."
                )
