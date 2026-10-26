"""Explicit, unmissable confirmation before the USB drive is erased."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QVBoxLayout,
)

from ..usb_detect import UsbDisk, format_size


class EraseConfirmDialog(QDialog):
    def __init__(self, disk: UsbDisk, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Erase this USB drive?")
        self.setModal(True)
        layout = QVBoxLayout(self)

        warning = QLabel(
            "<b>ALL data on the drive below will be permanently erased.</b><br>"
            "Check that this is the correct USB drive before continuing."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        form = QFormLayout()
        form.addRow("Device:", self._value(disk.friendly_name))
        form.addRow("Capacity:", self._value(format_size(disk.size)))
        form.addRow("Drive letter:", self._value(", ".join(f"{l}:" for l in disk.drive_letters) or "none"))
        form.addRow("Disk identifier:", self._value(disk.disk_id))
        if disk.serial_number:
            form.addRow("Serial number:", self._value(disk.serial_number))
        layout.addLayout(form)

        self.ack = QCheckBox("I understand that everything on this USB drive will be erased")
        layout.addWidget(self.ack)

        buttons = QDialogButtonBox()
        self.erase_button = QPushButton("Erase and create USB")
        self.erase_button.setObjectName("danger")
        self.erase_button.setEnabled(False)
        cancel = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.addButton(self.erase_button, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel.setDefault(True)
        cancel.setFocus()
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ack.toggled.connect(self.erase_button.setEnabled)
        layout.addWidget(buttons)

    @staticmethod
    def _value(text: str) -> QLabel:
        label = QLabel(text)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setStyleSheet("font-weight:600")
        return label
