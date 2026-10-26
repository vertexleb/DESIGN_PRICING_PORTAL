"""Revalidation immediately before writing and capacity checks."""

import dataclasses

import pytest
from conftest import GB, NVME, raw_disk, snapshot_json

from corex_boot.disk_safety import check_capacity, revalidate
from corex_boot.errors import DeviceDisconnectedError, DiskSafetyError, InsufficientCapacityError
from corex_boot.usb_detect import classify, parse_snapshot


def snap(*disks):
    return parse_snapshot(snapshot_json(raw_disk(0, **NVME), *disks))


def selected(**kw):
    return classify(snap(raw_disk(1, **kw))).eligible[0]


def test_unchanged_disk_passes():
    disk = selected()
    assert revalidate(disk, snap(raw_disk(1))).same_device(disk)


def test_disconnected_disk():
    with pytest.raises(DeviceDisconnectedError):
        revalidate(selected(), snap())


def test_different_disk_now_at_same_number_is_rejected():
    disk = selected()
    with pytest.raises(DiskSafetyError, match="no longer the drive you chose"):
        revalidate(disk, snap(raw_disk(1, uid="OTHER", serial="X")))


def test_same_disk_moved_to_new_number_is_not_silently_followed():
    disk = selected()
    with pytest.raises(DiskSafetyError):
        revalidate(disk, snap(raw_disk(5, uid=disk.unique_id, serial=disk.serial_number)))


def test_size_change_rejected():
    disk = selected()
    with pytest.raises(DiskSafetyError):
        revalidate(disk, snap(raw_disk(1, size=32 * GB)))


def test_selected_disk_became_internal_rejected():
    disk = selected()
    with pytest.raises(DiskSafetyError):
        revalidate(disk, snap(raw_disk(1, bus="SATA")))


def test_ambiguous_identifier_rejected():
    disk = selected()
    with pytest.raises(DiskSafetyError, match="unambiguously"):
        revalidate(disk, snap(raw_disk(1), raw_disk(2, uid=disk.unique_id)))


def test_tampered_selection_of_internal_disk_rejected():
    # Even if a bad selection reached the workflow, revalidation refuses the NVMe system disk.
    nvme = parse_snapshot(snapshot_json(raw_disk(0, **NVME))).disks[0]
    with pytest.raises(DiskSafetyError):
        revalidate(nvme, snap())


def test_capacity_ok_and_insufficient():
    disk = selected(size=8 * GB)
    check_capacity(disk, 3 * GB)
    small = dataclasses.replace(disk, size=2 * GB)
    with pytest.raises(InsufficientCapacityError, match="too small"):
        check_capacity(small, 3 * GB)


def test_capacity_respects_fat32_partition_cap():
    big = selected(size=128 * GB)
    with pytest.raises(InsufficientCapacityError):
        check_capacity(big, 40 * GB)


def test_production_erase_always_demands_usb_bus(monkeypatch):
    from corex_boot import backend

    captured = {}

    def fake_run(name, args=None, timeout=0):
        captured[name] = args
        return {"DriveLetter": "E"}

    monkeypatch.setattr(backend, "run_script", fake_run)
    disk = selected()
    assert backend._prepare(disk, "hbcd pe x64 long label") == "E:\\"
    args = captured["prepare_disk"]
    assert args["ExpectedBusType"] == "USB"
    assert args["DiskNumber"] == 1 and args["ExpectedUniqueId"] == disk.unique_id and args["ExpectedSize"] == disk.size
    assert args["Label"] == "HBCD_PE_X64"  # sanitised, max 11 chars for FAT32
