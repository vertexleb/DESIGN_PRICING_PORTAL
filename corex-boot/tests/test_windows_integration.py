"""Real-Windows tests. Skipped unless COREX_WINDOWS_INTEGRATION=1 (needs Administrator).

The virtual-disk tests additionally need COREX_DESTRUCTIVE_CI=1 and are meant for a
disposable CI VM: they create a 2 GB VHD, and they deliberately point the erase script at the
Windows system disk to prove the script refuses it. Do not set that variable on a real PC."""

import os
import subprocess

import pytest

from corex_boot import backend
from corex_boot.boot_verify import analyse_layout, mbr_problems, pbr_info
from corex_boot.errors import PowerShellError
from corex_boot.powershell import run_script
from corex_boot.usb_copy import copy_tree, list_tree, verify_tree
from corex_boot.usb_detect import classify, query_snapshot
from corex_boot.winio import read_head

pytestmark = [
    pytest.mark.windows_integration,
    pytest.mark.skipif(
        os.name != "nt" or os.environ.get("COREX_WINDOWS_INTEGRATION") != "1",
        reason="real Windows integration test",
    ),
]
destructive = pytest.mark.skipif(os.environ.get("COREX_DESTRUCTIVE_CI") != "1", reason="disposable CI VM only")


def ps(command: str) -> str:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def test_real_disk_scan_never_offers_system_disk():
    snap = query_snapshot()
    assert snap.disks, "Windows reported no disks at all"
    result = classify(snap)
    sys_letter = os.environ["SystemDrive"][0].upper()
    for disk in result.eligible:
        assert disk.bus_type.upper() == "USB"
        assert sys_letter not in disk.drive_letters and not disk.is_system and not disk.is_boot
    system_disks = [d for d in snap.disks if sys_letter in d.drive_letters]
    assert system_disks
    assert not any(d in result.eligible for d in system_disks)


@pytest.fixture
def vhd(tmp_path):
    path = tmp_path / "fake_usb.vhd"
    script = tmp_path / "diskpart.txt"
    script.write_text(f'create vdisk file="{path}" maximum=2048 type=expandable\n', encoding="ascii")
    subprocess.run(["diskpart", "/s", str(script)], check=True, capture_output=True)
    ps(f"Mount-DiskImage -ImagePath '{path}' | Out-Null")
    number = int(ps(f"(Get-DiskImage -ImagePath '{path}' | Get-Disk).Number"))
    disk = next(d for d in query_snapshot().disks if d.number == number)
    yield path, disk
    ps(f"Dismount-DiskImage -ImagePath '{path}' | Out-Null")


def prepare_args(disk, **overrides):
    args = {
        "DiskNumber": disk.number, "ExpectedUniqueId": disk.unique_id, "ExpectedSize": disk.size,
        "ExpectedBusType": disk.bus_type, "MaxPartitionBytes": 31 * 1024**3, "Label": "HBCD_TEST",
    }
    args.update(overrides)
    return args


@destructive
def test_virtual_disk_is_not_offered_as_usb(vhd):
    _, disk = vhd
    assert disk not in classify(query_snapshot()).eligible


@destructive
def test_erase_script_refuses_wrong_identity_and_bus(vhd):
    _, disk = vhd
    with pytest.raises(PowerShellError, match="SAFETY"):
        run_script("prepare_disk", prepare_args(disk, ExpectedUniqueId="NOT-THIS-DISK"))
    with pytest.raises(PowerShellError, match="SAFETY"):
        run_script("prepare_disk", prepare_args(disk, ExpectedBusType="USB"))
    with pytest.raises(PowerShellError, match="SAFETY"):
        run_script("prepare_disk", prepare_args(disk, ExpectedSize=disk.size + 1))
    assert ps(f"(Get-Disk -Number {disk.number}).PartitionStyle") == "RAW"  # untouched


@destructive
def test_erase_script_refuses_windows_system_disk():
    system = next(d for d in query_snapshot().disks if d.is_system or d.is_boot)
    with pytest.raises(PowerShellError, match="SAFETY"):
        run_script("prepare_disk", prepare_args(system))


@destructive
def test_end_to_end_on_virtual_disk(vhd, tmp_path):
    from test_iso_and_boot import build_iso

    _, disk = vhd
    iso = tmp_path / "winpe_like.iso"
    build_iso(iso)

    # Run twice: first on a RAW disk, then on an already-partitioned one (Clear-Disk path).
    for _ in range(2):
        data = run_script("prepare_disk", prepare_args(disk), timeout=600)
    usb_root = f"{data['DriveLetter']}:\\"

    iso_root, _label = backend._mount(iso)
    try:
        entries = list_tree(iso_root)
        layout = analyse_layout(entries)
        hashes = copy_tree(iso_root, usb_root, entries)
        backend._flush(usb_root)
        verify_tree(usb_root, entries, hashes)  # uncached (FILE_FLAG_NO_BUFFERING) read-back
    finally:
        backend._dismount(iso)

    assert {e.relpath for e in list_tree(usb_root)} == {e.relpath for e in entries}
    assert layout.supports_uefi and layout.supports_bios
    mbr = read_head(disk.physical_path, 512)
    assert mbr_problems(mbr) == []
    is_fat32, loader = pbr_info(read_head(rf"\\.\{usb_root[0]}:", 64 * 1024))
    assert is_fat32
    print("FAT32 boot sector loader:", loader)
    assert loader == "BOOTMGR"
