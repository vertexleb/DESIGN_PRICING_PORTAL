"""Main window: pick a USB drive, press one button."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__
from ..backend import Backend
from ..config import log_dir
from ..usb_detect import Classification, UsbDisk, format_size
from ..workflow import Workflow
from .confirm_dialog import EraseConfirmDialog
from .workers import RunWorker, ScanWorker, WorkerUI

log = logging.getLogger(__name__)

WM_DEVICECHANGE = 0x0219
PLACEHOLDER = "Select a USB drive..."


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 16)
    layout.setSpacing(10)
    heading = QLabel(title)
    heading.setObjectName("cardTitle")
    layout.addWidget(heading)
    return frame, layout


class MainWindow(QMainWindow):
    def __init__(self, backend: Backend, *, admin: bool = True, confirm_erase=None) -> None:
        super().__init__()
        self.backend = backend
        self.disks: list[UsbDisk] = []
        self.scan_worker: ScanWorker | None = None
        self.run_worker: RunWorker | None = None
        self._rescan_pending = False
        # Injectable for tests; defaults to the modal dialog.
        self.confirm_erase = confirm_erase or (lambda disk: EraseConfirmDialog(disk, self).exec() == EraseConfirmDialog.DialogCode.Accepted)

        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(620)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(14)

        title = QLabel(APP_NAME)
        title.setObjectName("title")
        subtitle = QLabel("Creates a bootable Hiren's BootCD PE USB drive from the official download.")
        subtitle.setObjectName("subtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        self.admin_banner = QLabel(
            "Corex Boot is not running as Administrator. Close it, right-click it and choose "
            "'Run as administrator' to create a USB drive."
        )
        self.admin_banner.setObjectName("banner")
        self.admin_banner.setWordWrap(True)
        self.admin_banner.setVisible(not admin)
        outer.addWidget(self.admin_banner)

        # --- USB selection -------------------------------------------------
        card, body = _card("1.  Choose the USB drive")
        row = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo.currentIndexChanged.connect(self._on_selection_changed)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        row.addWidget(self.combo, 1)
        row.addWidget(self.refresh_button)
        body.addLayout(row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        self.fields: dict[str, QLabel] = {}
        for i, (key, label) in enumerate(
            [("name", "Device"), ("capacity", "Capacity"), ("letters", "Drive letter"), ("diskid", "Disk identifier")]
        ):
            name = QLabel(label)
            name.setObjectName("fieldLabel")
            value = QLabel("-")
            value.setObjectName("fieldValue")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(name, i // 2, (i % 2) * 2)
            grid.addWidget(value, i // 2, (i % 2) * 2 + 1)
            self.fields[key] = value
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        body.addLayout(grid)
        self.scan_hint = QLabel("Looking for USB drives...")
        self.scan_hint.setObjectName("hint")
        self.scan_hint.setWordWrap(True)
        body.addWidget(self.scan_hint)
        outer.addWidget(card)

        # --- Create --------------------------------------------------------
        card, body = _card("2.  Create the bootable USB")
        buttons = QHBoxLayout()
        self.start_button = QPushButton("Download && Create USB")
        self.start_button.setObjectName("primary")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        body.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        body.addWidget(self.progress)
        self.status_label = QLabel("Ready. Select a USB drive to begin.")
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)
        body.addWidget(self.status_label)
        self.download_label = QLabel("Download: not started")
        self.download_label.setObjectName("downloadText")
        body.addWidget(self.download_label)
        outer.addWidget(card)

        # --- Completion ----------------------------------------------------
        self.done_label = QLabel()
        self.done_label.setWordWrap(True)
        self.done_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.done_label.setVisible(False)
        outer.addWidget(self.done_label)
        self.details_label = QLabel()
        self.details_label.setObjectName("details")
        self.details_label.setWordWrap(True)
        self.details_label.setVisible(False)
        outer.addWidget(self.details_label)

        footer = QHBoxLayout()
        version = QLabel(f"{APP_NAME} {__version__}  -  source: hirensbootcd.org")
        version.setObjectName("hint")
        logs = QPushButton("Open log folder")
        logs.setFlat(True)
        logs.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir()))))
        footer.addWidget(version)
        footer.addStretch(1)
        footer.addWidget(logs)
        outer.addStretch(1)
        outer.addLayout(footer)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(1500)
        self._debounce.timeout.connect(self.refresh)

        self._load_style()
        self._populate([])
        QTimer.singleShot(0, self.refresh)

    # ------------------------------------------------------------------ style
    def _load_style(self) -> None:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        for candidate in (base / "corex_boot" / "gui" / "style.qss", Path(__file__).with_name("style.qss")):
            if candidate.exists():
                self.setStyleSheet(candidate.read_text(encoding="utf-8"))
                return

    # ------------------------------------------------------------ USB list
    @property
    def busy(self) -> bool:
        return self.run_worker is not None and self.run_worker.isRunning()

    def selected_disk(self) -> UsbDisk | None:
        idx = self.combo.currentIndex()
        if idx <= 0 or idx > len(self.disks):
            return None
        return self.disks[idx - 1]

    def refresh(self) -> None:
        if self.busy:
            return
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self._rescan_pending = True
            return
        self.refresh_button.setEnabled(False)
        self.scan_hint.setText("Looking for USB drives...")
        self.scan_worker = ScanWorker(self.backend, self)
        self.scan_worker.done.connect(self._on_scan_done)
        self.scan_worker.failed.connect(self._on_scan_failed)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _on_scan_finished(self) -> None:
        self.refresh_button.setEnabled(not self.busy)
        if self._rescan_pending:
            self._rescan_pending = False
            QTimer.singleShot(0, self.refresh)

    def _on_scan_failed(self, message: str) -> None:
        self._populate([])
        self.scan_hint.setText(message)

    def _on_scan_done(self, result: Classification) -> None:
        if self.busy:
            return
        previous = self.selected_disk()
        self._populate(result.eligible, keep=previous)
        if not result.eligible:
            hint = "No USB drive found. Plug in a USB flash drive (8 GB or larger) and press Refresh."
        elif len(result.eligible) == 1:
            hint = "1 USB drive found. Select it above."
        else:
            hint = f"{len(result.eligible)} USB drives found. Select the one to erase."
        if result.rejected:
            hint += f"  ({len(result.rejected)} internal or unsafe disk(s) hidden.)"
            self.scan_hint.setToolTip(
                "\n".join(f"{d.friendly_name} (Disk {d.number}): {', '.join(r)}" for d, r in result.rejected)
            )
        if previous is not None and self.selected_disk() is None:
            hint = "The previously selected USB drive is no longer available. " + hint
        self.scan_hint.setText(hint)

    def _populate(self, disks: list[UsbDisk], keep: UsbDisk | None = None) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        self.disks = list(disks)
        self.combo.addItem(PLACEHOLDER)
        for disk in self.disks:
            self.combo.addItem(disk.describe())
        index = 0
        if keep is not None:
            # Keep the user's choice only if it is exactly the same device.
            for i, disk in enumerate(self.disks, start=1):
                if disk.same_device(keep):
                    index = i
        self.combo.setCurrentIndex(index)
        self.combo.blockSignals(False)
        self._on_selection_changed()

    def _on_selection_changed(self, *_args) -> None:
        disk = self.selected_disk()
        if disk is None:
            for value in self.fields.values():
                value.setText("-")
        else:
            self.fields["name"].setText(disk.friendly_name)
            self.fields["capacity"].setText(format_size(disk.size))
            self.fields["letters"].setText(", ".join(f"{l}:" for l in disk.drive_letters) or "none")
            self.fields["diskid"].setText(disk.disk_id)
        self.start_button.setEnabled(disk is not None and not self.busy)

    # --------------------------------------------------------------- run
    def start(self) -> None:
        disk = self.selected_disk()
        if disk is None or self.busy:
            return
        if not self.confirm_erase(disk):
            self.status_label.setText("Cancelled. Nothing was written.")
            return
        self.done_label.setVisible(False)
        self.details_label.setVisible(False)
        self.progress.setValue(0)
        self.download_label.setText("Download: starting...")

        def factory(worker: RunWorker, cancel):
            return Workflow(disk, WorkerUI(worker), self.backend, cancel)

        self.run_worker = RunWorker(factory, self)
        w = self.run_worker
        w.stage.connect(self._on_stage)
        w.progress.connect(lambda p: self.progress.setValue(int(p * 10)))
        w.download.connect(lambda t: self.download_label.setText(f"Download: {t}"))
        w.confirm_request.connect(self._on_confirm_request)
        w.succeeded.connect(self._on_success)
        w.failed.connect(self._on_failure)
        w.cancelled.connect(self._on_cancelled)
        w.finished.connect(self._on_run_finished)
        self._set_busy(True)
        w.start()

    def cancel(self) -> None:
        if self.run_worker is not None:
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling...")
            self.run_worker.cancel()

    def _set_busy(self, busy: bool) -> None:
        self.combo.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.start_button.setEnabled(not busy and self.selected_disk() is not None)
        self.cancel_button.setEnabled(busy)

    def _on_stage(self, text: str) -> None:
        self.status_label.setText(text)
        if self.run_worker is not None and self.run_worker.workflow.writing:
            # Once the drive is erased, stopping half-way only leaves an unusable USB.
            self.cancel_button.setEnabled(False)

    def _on_confirm_request(self, title: str, text: str, reply: dict) -> None:
        box = QMessageBox(QMessageBox.Icon.Warning, title, text, parent=self)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        reply["answer"] = box.exec() == QMessageBox.StandardButton.Yes
        reply["event"].set()

    def _on_success(self, result) -> None:
        self.progress.setValue(1000)
        self._set_done_style("doneOk")
        self.done_label.setText("✔  Bootable USB Ready")
        lines = [f"✓ {c}" for c in result.checks] + [f"⚠ {w}" for w in result.warnings]
        lines.append("Final confirmation: boot a computer from this USB drive (Boot menu key, usually F12, F11 or Esc).")
        self.details_label.setText("\n".join(lines))
        self.done_label.setVisible(True)
        self.details_label.setVisible(True)
        self.status_label.setText("Bootable USB Ready")

    def _set_done_style(self, name: str) -> None:
        self.done_label.setObjectName(name)
        self.done_label.style().unpolish(self.done_label)
        self.done_label.style().polish(self.done_label)

    def _show_failure(self, message: str) -> None:
        self._set_done_style("doneFail")
        self.done_label.setText("✖  " + message)
        self.done_label.setVisible(True)

    def _on_failure(self, message: str, usb_modified: bool) -> None:
        self.status_label.setText("Failed.")
        if usb_modified:
            message += "\n\nThe USB drive was erased but is not finished - it will not boot until Corex Boot completes successfully."
        self._show_failure(message)

    def _on_cancelled(self, message: str) -> None:
        self.status_label.setText(message)
        self.download_label.setText("Download: stopped")

    def _on_run_finished(self) -> None:
        self._set_busy(False)
        QTimer.singleShot(0, self.refresh)

    # ------------------------------------------------------------ events
    def nativeEvent(self, event_type, message):  # noqa: N802 (Qt naming)
        if os.name == "nt" and event_type == b"windows_generic_MSG":
            from ctypes import wintypes

            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_DEVICECHANGE and not self.busy:
                self._debounce.start()
        return super().nativeEvent(event_type, message)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.busy:
            writing = self.run_worker.workflow.writing
            text = (
                "The USB drive is being written. Closing now leaves it unusable. Close anyway?"
                if writing else "A download is in progress. Stop and close? (It will resume next time.)"
            )
            if QMessageBox.question(self, APP_NAME, text) != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.run_worker.cancel()
            self.run_worker.wait(15000)
        event.accept()
