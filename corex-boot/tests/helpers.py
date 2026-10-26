"""Fake Windows backend for workflow/GUI tests. Directories stand in for the mounted ISO
and the USB volume; byte strings stand in for the MBR and FAT32 boot sector."""

from __future__ import annotations

import hashlib
import shutil
import struct
from dataclasses import dataclass, field
from pathlib import Path

from conftest import NVME, raw_disk, snapshot_json

from corex_boot import iso_verify, usb_copy
from corex_boot.backend import Backend
from corex_boot.source import IsoRelease
from corex_boot.usb_detect import classify, parse_snapshot

ISO_FILES = {
    "bootmgr": b"BOOTMGR-BINARY" * 100,
    "EFI/BOOT/BOOTX64.EFI": b"MZ-EFI" * 500,
    "Boot/BCD": b"regf-bios" * 50,
    "EFI/Microsoft/Boot/BCD": b"regf-efi" * 50,
    "sources/boot.wim": b"MSWIM" * 200_000,
    "HBCD_PE.ini": b"[HBCD]",
}


def fake_iso_bytes() -> bytes:
    data = bytearray(64 * 2048)
    data[16 * 2048: 16 * 2048 + 6] = b"\x01CD001"
    return bytes(data)


def good_mbr(active=True, ptype=0x0C, boot_code=True) -> bytes:
    sector = bytearray(512)
    if boot_code:
        sector[:3] = b"\x33\xc0\x8e"
    sector[446] = 0x80 if active else 0
    sector[446 + 4] = ptype
    sector[446 + 8: 446 + 16] = struct.pack("<II", 2048, 1_000_000)
    sector[510:512] = b"\x55\xaa"
    return bytes(sector)


def good_pbr(loader=b"BOOTMGR") -> bytes:
    head = bytearray(16 * 512)
    head[82:90] = b"FAT32   "
    head[510:512] = b"\x55\xaa"
    head[12 * 512 + 100: 12 * 512 + 100 + len(loader)] = loader
    return bytes(head)


@dataclass
class FakeState:
    calls: list = field(default_factory=list)
    disks: list = field(default_factory=lambda: [raw_disk(0, **NVME), raw_disk(1)])
    checksums: dict | None = None
    iso_bytes: bytes = field(default_factory=fake_iso_bytes)
    iso_files: dict = field(default_factory=lambda: dict(ISO_FILES))
    admin: bool = True
    mbr: bytes = field(default_factory=good_mbr)
    pbr: bytes = field(default_factory=good_pbr)
    fail_copy_with: Exception | None = None
    unplug_during_copy: bool = False
    on_download: object = None  # callable(state) run mid-download, e.g. to unplug the USB
    corrupt_on_usb: str | None = None
    download_error: Exception | None = None
    reported_total: int | None = None  # size the server announces
    prepare_error: Exception | None = None


class FakeDownloader:
    def __init__(self, state, url, dest, progress=None, on_total=None, cancel=None):
        self.state, self.dest = state, Path(dest)
        self.progress, self.on_total = progress, on_total

    def run(self):
        self.state.calls.append("download")
        if self.state.download_error:
            raise self.state.download_error
        if self.state.on_download:
            self.state.on_download(self.state)
        data = self.state.iso_bytes
        self.on_total(self.state.reported_total or len(data))
        self.dest.write_bytes(data)
        self.progress(len(data), len(data), 1e6)
        return self.dest

    def discard(self):
        self.state.calls.append("discard")
        self.dest.unlink(missing_ok=True)


def selected_disk(state: FakeState):
    return classify(parse_snapshot(snapshot_json(*state.disks))).eligible[0]


def make_backend(tmp_path: Path, state: FakeState) -> Backend:
    iso_root = tmp_path / "iso"
    usb_root = tmp_path / "usb"
    cache = tmp_path / "cache"
    cache.mkdir(exist_ok=True)
    if state.checksums is None:
        state.checksums = {"sha256": hashlib.sha256(state.iso_bytes).hexdigest()}

    def query():
        state.calls.append("query")
        return parse_snapshot(snapshot_json(*state.disks))

    def mount(path):
        state.calls.append("mount")
        shutil.rmtree(iso_root, ignore_errors=True)
        for rel, data in state.iso_files.items():
            p = iso_root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        return str(iso_root), "HBCD_PE_X64"

    def prepare(disk, label):
        state.calls.append(("prepare", disk.number, disk.unique_id, label))
        if state.prepare_error:
            raise state.prepare_error
        shutil.rmtree(usb_root, ignore_errors=True)
        usb_root.mkdir()
        return str(usb_root)

    def copy(src, dst, entries, progress=None, cancel=None):
        state.calls.append("copy")
        if state.unplug_during_copy:
            state.disks = [d for d in state.disks if d["Number"] != 1]
            raise OSError(1167, "The device is not connected")
        if state.fail_copy_with:
            raise state.fail_copy_with
        hashes = usb_copy.copy_tree(src, dst, entries, progress, cancel)
        if state.corrupt_on_usb:
            (Path(dst) / state.corrupt_on_usb).write_bytes(b"garbage")
        return hashes

    return Backend(
        is_admin=lambda: state.admin,
        query_snapshot=query,
        discover_release=lambda: IsoRelease(
            url="https://www.hirensbootcd.org/files/HBCD_PE_x64.iso", filename="HBCD_PE_x64.iso",
            version="9.9.9", checksums=state.checksums,
        ),
        make_downloader=lambda url, dest, **kw: FakeDownloader(state, url, dest, **kw),
        check_iso_structure=lambda p: iso_verify.check_iso_structure(p, min_size=0),
        verify_checksum=iso_verify.verify_checksum,
        mount_iso=mount,
        dismount_iso=lambda p: state.calls.append("dismount"),
        list_tree=usb_copy.list_tree,
        prepare_disk=prepare,
        copy_tree=copy,
        flush_volume=lambda root: state.calls.append("flush"),
        verify_tree=lambda *a, **kw: usb_copy.verify_tree(*a, reader=_plain_reader, **kw),
        read_mbr=lambda disk: state.mbr,
        read_volume_head=lambda root: state.pbr,
        cache_dir=lambda: cache,
    )


def _plain_reader(path):
    with open(path, "rb") as fh:
        while block := fh.read(1 << 20):
            yield block


class RecordingUI:
    def __init__(self, answer=True):
        self.stages, self.percent, self.downloads, self.questions = [], [], [], []
        self.answer = answer

    def stage(self, text):
        self.stages.append(text)

    def progress(self, p):
        self.percent.append(p)

    def download_status(self, text):
        self.downloads.append(text)

    def confirm(self, title, text):
        self.questions.append(title)
        return self.answer
