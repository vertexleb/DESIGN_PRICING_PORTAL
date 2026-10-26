"""End-to-end workflow against the fake backend: every QA scenario that can be
exercised without real hardware. The invariant checked throughout: the disk is
only ever prepared (erased) when every precondition holds, and only the selected disk."""

import pytest
from conftest import raw_disk
from helpers import FakeState, RecordingUI, good_mbr, good_pbr, make_backend, selected_disk

from corex_boot.errors import (
    BootVerificationError,
    CancelledError,
    ChecksumMismatchError,
    DeviceDisconnectedError,
    DiskSafetyError,
    DownloadError,
    InsufficientCapacityError,
    InvalidIsoError,
    PermissionDeniedError,
    UsbWriteError,
)
from corex_boot.workflow import Workflow


def run(tmp_path, state, ui=None):
    ui = ui or RecordingUI()
    wf = Workflow(selected_disk(state), ui, make_backend(tmp_path, state))
    return wf, ui, wf.run


def prepared(state):
    return [c for c in state.calls if isinstance(c, tuple) and c[0] == "prepare"]


def test_successful_creation(tmp_path):
    state = FakeState()
    wf, ui, go = run(tmp_path, state)
    result = go()
    assert result.iso_verified
    assert prepared(state) == [("prepare", 1, "USBSTOR\\DISK&VEN_1", "HBCD_PE_X64")]
    assert (tmp_path / "usb" / "EFI/BOOT/BOOTX64.EFI").exists()
    assert ui.stages[-1] == "Bootable USB Ready"
    assert ui.percent[-1] == 100
    assert any("SHA256 matches" in c for c in result.checks)
    assert any("read back" in c for c in result.checks)
    assert any("Legacy BIOS" in c for c in result.checks)
    assert result.warnings == []
    # Temporary files cleaned after success; ISO dismounted.
    assert "discard" in state.calls and "dismount" in state.calls
    assert not (tmp_path / "cache" / "HBCD_PE_x64.iso").exists()
    # Disk revalidated right before prepare.
    i = state.calls.index(prepared(state)[0])
    assert state.calls[i - 1] == "query"


def test_insufficient_permissions(tmp_path):
    state = FakeState(admin=False)
    with pytest.raises(PermissionDeniedError):
        run(tmp_path, state)[2]()
    assert state.calls == []


def test_usb_disconnected_during_download(tmp_path):
    state = FakeState(on_download=lambda s: s.disks.pop())
    with pytest.raises(DeviceDisconnectedError):
        run(tmp_path, state)[2]()
    assert prepared(state) == []


def test_usb_swapped_for_other_drive_during_download(tmp_path):
    def swap(s):
        s.disks[1] = raw_disk(1, name="Other Stick", uid="OTHER", serial="OTHER")

    state = FakeState(on_download=swap)
    with pytest.raises(DiskSafetyError):
        run(tmp_path, state)[2]()
    assert prepared(state) == []


def test_usb_disconnected_during_write(tmp_path):
    state = FakeState(unplug_during_copy=True)
    wf, ui, go = run(tmp_path, state)
    with pytest.raises(DeviceDisconnectedError):
        go()
    assert wf.writing  # GUI tells the user the stick is incomplete
    assert "dismount" in state.calls


def test_usb_write_failure(tmp_path):
    state = FakeState(fail_copy_with=OSError(5, "I/O error"))
    with pytest.raises(UsbWriteError, match="Writing to the USB drive failed"):
        run(tmp_path, state)[2]()


def test_readback_mismatch_detected(tmp_path):
    state = FakeState(corrupt_on_usb="sources/boot.wim")
    with pytest.raises(UsbWriteError, match="do not match"):
        run(tmp_path, state)[2]()


def test_download_interrupted(tmp_path):
    state = FakeState(download_error=DownloadError("The download was interrupted repeatedly."))
    with pytest.raises(DownloadError):
        run(tmp_path, state)[2]()
    assert prepared(state) == []


def test_checksum_mismatch_deletes_iso_and_never_writes(tmp_path):
    state = FakeState(checksums={"sha256": "0" * 64})
    with pytest.raises(ChecksumMismatchError):
        run(tmp_path, state)[2]()
    assert prepared(state) == [] and "discard" in state.calls


def test_invalid_iso_file(tmp_path):
    state = FakeState(iso_bytes=b"<html>not an iso</html>" * 1000)
    with pytest.raises(InvalidIsoError):
        run(tmp_path, state)[2]()
    assert prepared(state) == []


def test_iso_without_uefi_loader_rejected_before_erase(tmp_path):
    state = FakeState()
    del state.iso_files["EFI/BOOT/BOOTX64.EFI"]
    with pytest.raises(InvalidIsoError, match="BOOTX64"):
        run(tmp_path, state)[2]()
    assert prepared(state) == []


def test_unverifiable_checksum_declined_writes_nothing(tmp_path):
    state = FakeState(checksums={})
    ui = RecordingUI(answer=False)
    with pytest.raises(CancelledError, match="could not be verified"):
        run(tmp_path, state, ui)[2]()
    assert ui.questions == ["Checksum not available"]
    assert "download" not in state.calls and prepared(state) == []


def test_unverifiable_checksum_accepted_is_reported_as_unverified(tmp_path):
    state = FakeState(checksums={})
    result = run(tmp_path, state, RecordingUI(answer=True))[2]()
    assert not result.iso_verified
    assert any("NOT checksum-verified" in w for w in result.warnings)
    assert not any("matches" in c and "SHA" in c for c in result.checks)


def test_insufficient_usb_capacity(tmp_path):
    state = FakeState()
    state.disks[1] = raw_disk(1, size=1_100_000_000)
    state.reported_total = 3_000_000_000
    with pytest.raises(InsufficientCapacityError):
        run(tmp_path, state)[2]()
    assert prepared(state) == []


def test_incorrect_disk_selection_internal_disk(tmp_path):
    state = FakeState()
    from corex_boot.usb_detect import parse_snapshot
    from conftest import snapshot_json

    nvme = parse_snapshot(snapshot_json(*state.disks)).disks[0]
    wf = Workflow(nvme, RecordingUI(), make_backend(tmp_path, state))
    with pytest.raises(DiskSafetyError):
        wf.run()
    assert prepared(state) == [] and "download" not in state.calls


def test_bad_partition_table_fails_verification(tmp_path):
    state = FakeState(mbr=good_mbr(active=False))
    with pytest.raises(BootVerificationError, match="not marked active"):
        run(tmp_path, state)[2]()


def test_not_fat32_fails_verification(tmp_path):
    state = FakeState(pbr=b"\0" * 8192)
    with pytest.raises(BootVerificationError, match="FAT32"):
        run(tmp_path, state)[2]()


def test_missing_legacy_boot_code_is_a_warning_not_a_claim(tmp_path):
    state = FakeState(pbr=good_pbr(loader=b"NTLDR"))
    result = run(tmp_path, state)[2]()
    assert any("Legacy BIOS boot code could not be confirmed" in w for w in result.warnings)
    assert not any("Legacy BIOS:" in c for c in result.checks)


def test_cancel_before_writing(tmp_path):
    state = FakeState()
    ui = RecordingUI()
    wf = Workflow(selected_disk(state), ui, make_backend(tmp_path, state))
    wf.cancel.set()
    with pytest.raises(CancelledError, match="Nothing was written"):
        wf.run()
    assert prepared(state) == []


def test_erase_script_safety_refusal_reports_nothing_written(tmp_path):
    from corex_boot.errors import PowerShellError

    state = FakeState(prepare_error=PowerShellError("SAFETY: disk 1 identity changed. Nothing was written."))
    wf, _, go = run(tmp_path, state)
    with pytest.raises(DiskSafetyError, match="identity changed"):
        go()
    assert not wf.writing


def test_prepare_failure_reports_usb_write_error(tmp_path):
    from corex_boot.errors import PowerShellError

    state = FakeState(prepare_error=PowerShellError("The media is write protected."))
    wf, _, go = run(tmp_path, state)
    with pytest.raises(UsbWriteError, match="write protected"):
        go()
    assert wf.writing
