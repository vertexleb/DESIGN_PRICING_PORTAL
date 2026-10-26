"""GUI behaviour (headless). Key safety property: a USB drive is never selected automatically."""

import time

import pytest
from conftest import raw_disk
from helpers import FakeState, make_backend

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from corex_boot.gui.main_window import PLACEHOLDER, MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_for(app, cond, timeout=20.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if cond():
            return
        time.sleep(0.01)
    raise AssertionError("timed out")


def make_window(app, tmp_path, state, confirm=lambda disk: True):
    win = MainWindow(make_backend(tmp_path, state), confirm_erase=confirm)
    wait_for(app, lambda: win.scan_worker is not None and win.scan_worker.isFinished())
    app.processEvents()
    return win


def test_title_and_controls(app, tmp_path):
    win = make_window(app, tmp_path, FakeState())
    assert win.windowTitle() == "Corex Boot"
    assert win.start_button.text().replace("&&", "&") == "Download & Create USB"
    assert win.refresh_button.text() == "Refresh"


def test_no_usb_connected(app, tmp_path):
    state = FakeState()
    state.disks = state.disks[:1]  # only the internal NVMe
    win = make_window(app, tmp_path, state)
    assert win.combo.count() == 1 and win.combo.itemText(0) == PLACEHOLDER
    assert not win.start_button.isEnabled()
    assert "No USB drive found" in win.scan_hint.text()
    assert "1 internal or unsafe disk" in win.scan_hint.text()


def test_one_usb_is_listed_but_not_auto_selected(app, tmp_path):
    win = make_window(app, tmp_path, FakeState())
    assert win.combo.count() == 2
    assert win.combo.currentIndex() == 0
    assert win.selected_disk() is None
    assert not win.start_button.isEnabled()
    win.combo.setCurrentIndex(1)
    assert win.start_button.isEnabled()
    assert win.fields["name"].text() == "SanDisk Ultra"
    assert win.fields["capacity"].text() == "16.0 GB"
    assert win.fields["letters"].text() == "E:"
    assert "PhysicalDrive1" in win.fields["diskid"].text()


def test_multiple_usb_not_auto_selected(app, tmp_path):
    state = FakeState()
    state.disks.append(raw_disk(2, name="Kingston DataTraveler", letters=("F",)))
    win = make_window(app, tmp_path, state)
    assert win.combo.count() == 3 and win.combo.currentIndex() == 0


def test_refresh_keeps_same_device_and_drops_replaced_one(app, tmp_path):
    state = FakeState()
    win = make_window(app, tmp_path, state)
    win.combo.setCurrentIndex(1)
    win.refresh()
    wait_for(app, lambda: win.scan_worker.isFinished())
    app.processEvents()
    assert win.selected_disk() is not None and win.selected_disk().number == 1

    state.disks[1] = raw_disk(1, name="Other", uid="OTHER", serial="OTHER")
    win.refresh()
    wait_for(app, lambda: win.scan_worker.isFinished())
    app.processEvents()
    assert win.selected_disk() is None
    assert "no longer available" in win.scan_hint.text()


def test_declining_erase_confirmation_does_nothing(app, tmp_path):
    state = FakeState()
    win = make_window(app, tmp_path, state, confirm=lambda disk: False)
    win.combo.setCurrentIndex(1)
    win.start()
    assert win.run_worker is None
    assert "Nothing was written" in win.status_label.text()
    assert not any(isinstance(c, tuple) for c in state.calls)


def test_full_run_shows_bootable_usb_ready(app, tmp_path):
    state = FakeState()
    confirmed = []
    win = make_window(app, tmp_path, state, confirm=lambda disk: confirmed.append(disk) or True)
    win.combo.setCurrentIndex(1)
    win.start()
    assert confirmed[0].number == 1
    assert not win.combo.isEnabled() and not win.refresh_button.isEnabled()
    wait_for(app, lambda: win.run_worker.isFinished())
    app.processEvents()
    assert win.done_label.isVisible() or win.done_label.text()
    assert "Bootable USB Ready" in win.done_label.text()
    assert win.progress.value() == 1000
    assert "read back" in win.details_label.text()


def test_failure_is_shown(app, tmp_path):
    state = FakeState(fail_copy_with=OSError(5, "I/O error"))
    win = make_window(app, tmp_path, state)
    win.combo.setCurrentIndex(1)
    win.start()
    wait_for(app, lambda: win.run_worker.isFinished())
    app.processEvents()
    assert "Writing to the USB drive failed" in win.done_label.text()
    assert "erased but is not finished" in win.done_label.text()
    assert "Bootable USB Ready" not in win.done_label.text()
