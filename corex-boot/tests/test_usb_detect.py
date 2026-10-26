"""USB detection: which disks are offered to the user."""

from conftest import GB, NVME, raw_disk, snapshot_json

from corex_boot.usb_detect import classify, format_size, parse_snapshot


def eligible(*disks, **kw):
    return classify(parse_snapshot(snapshot_json(*disks, **kw))).eligible


def test_no_usb_connected_offers_nothing():
    result = classify(parse_snapshot(snapshot_json(raw_disk(0, **NVME))))
    assert result.eligible == []
    assert len(result.rejected) == 1
    reasons = result.rejected[0][1]
    assert any("not a USB device" in r for r in reasons)
    assert any("Windows boots" in r for r in reasons)


def test_empty_machine_output():
    assert classify(parse_snapshot({})).eligible == []
    assert classify(parse_snapshot(snapshot_json())).eligible == []


def test_one_usb_connected():
    disks = eligible(raw_disk(0, **NVME), raw_disk(1, letters=("E",)))
    assert [d.number for d in disks] == [1]
    d = disks[0]
    assert d.physical_path == r"\\.\PhysicalDrive1"
    assert d.drive_letters == ("E",)
    assert "SanDisk Ultra" in d.describe() and "16.0 GB" in d.describe() and "Disk 1" in d.describe()


def test_multiple_usb_drives_sorted():
    disks = eligible(raw_disk(3, name="B"), raw_disk(0, **NVME), raw_disk(2, name="A"))
    assert [d.number for d in disks] == [2, 3]


def test_single_disk_object_not_wrapped_in_list():
    # PowerShell may emit a lone object instead of a one-element array.
    data = snapshot_json()
    data["Disks"] = raw_disk(1)
    data["Disks"]["DriveLetters"] = "F"
    disks = classify(parse_snapshot(data)).eligible
    assert len(disks) == 1 and disks[0].drive_letters == ("F",)


def test_internal_disks_never_offered():
    disks = eligible(
        raw_disk(0, **NVME),
        raw_disk(1, name="SATA HDD", bus="SATA", letters=("D",)),
        raw_disk(2, name="RAID", bus="RAID", letters=()),
        raw_disk(3, name="VHD", bus="File Backed Virtual", letters=("V",)),
    )
    assert disks == []


def test_usb_disk_that_hosts_windows_is_rejected():
    # Windows-To-Go style: USB bus but it is the system disk.
    disk = raw_disk(1, letters=("C",), boot=True, system=True)
    assert eligible(disk) == []
    disk = raw_disk(1, letters=("C",))  # flags missing, but holds the system drive
    assert eligible(disk) == []


def test_usb_disk_with_page_file_rejected():
    assert eligible(raw_disk(1, letters=("P",)), page_files=("C", "P")) == []


def test_card_reader_without_media_rejected():
    assert eligible(raw_disk(1, size=0, letters=())) == []


def test_too_small_and_too_large_rejected():
    assert eligible(raw_disk(1, size=512 * 1000**2)) == []
    assert eligible(raw_disk(1, size=4 * 1000 * GB)) == []


def test_write_protected_rejected():
    assert eligible(raw_disk(1, readonly=True)) == []


def test_duplicate_identifier_is_ambiguous_and_rejected():
    disks = eligible(raw_disk(1, uid="SAME"), raw_disk(2, uid="SAME"), raw_disk(3))
    assert [d.number for d in disks] == [3]


def test_missing_identifier_rejected():
    assert eligible(raw_disk(1, uid="")) == []


def test_format_size():
    assert format_size(16 * GB) == "16.0 GB"
    assert format_size(999) == "999 bytes"
    assert format_size(1500 * GB) == "1.5 TB"
