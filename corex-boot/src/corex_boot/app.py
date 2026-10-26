"""Application entry point."""

from __future__ import annotations

import logging
import os
import sys


def self_test(out_path: str) -> int:
    """Non-interactive check of a built EXE: bundle contents, GUI toolkit, read-only disk scan."""
    import json
    import traceback

    report: dict = {"ok": False}
    try:
        from PySide6 import QtWidgets

        report["qt"] = QtWidgets.__name__  # proves Qt is bundled

        from . import __version__
        from .powershell import scripts_dir
        from .usb_detect import classify, query_snapshot

        report["version"] = __version__
        report["scripts"] = sorted(p.name for p in scripts_dir().glob("*.ps1"))
        result = classify(query_snapshot())
        report["eligible"] = [d.describe() for d in result.eligible]
        report["rejected"] = [[d.describe(), reasons] for d, reasons in result.rejected]
        report["ok"] = len(report["scripts"]) == 5
    except Exception:  # noqa: BLE001
        report["error"] = traceback.format_exc()
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return 0 if report["ok"] else 1


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        return self_test(sys.argv[2])

    from . import APP_ID, APP_NAME
    from .admin import is_admin, relaunch_as_admin
    from .logging_setup import setup_logging

    setup_logging()
    log = logging.getLogger("corex_boot")

    def excepthook(exc_type, exc, tb):
        log.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = excepthook

    admin = is_admin()
    if os.name == "nt" and not admin and "--no-elevate" not in sys.argv:
        if relaunch_as_admin():
            return 0
        log.warning("Running without Administrator rights (UAC declined)")

    if os.name == "nt":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .backend import windows_backend
    from .gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    icon_base = getattr(sys, "_MEIPASS", None)
    if icon_base:
        app.setWindowIcon(QIcon(os.path.join(icon_base, "corex_boot.ico")))
    window = MainWindow(windows_backend(), admin=admin)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
