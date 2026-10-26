"""Background threads so disk scans and the long-running workflow never block the GUI."""

from __future__ import annotations

import logging
import threading
import traceback

from PySide6.QtCore import QObject, QThread, Signal

from ..backend import Backend
from ..errors import CancelledError, CorexError
from ..usb_detect import classify
from ..workflow import Workflow

log = logging.getLogger(__name__)


class ScanWorker(QThread):
    done = Signal(object)  # Classification
    failed = Signal(str)

    def __init__(self, backend: Backend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.backend = backend

    def run(self) -> None:
        try:
            self.done.emit(classify(self.backend.query_snapshot()))
        except CorexError as exc:
            log.exception("Disk scan failed")
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - never crash the GUI thread
            log.exception("Disk scan crashed")
            self.failed.emit(f"Could not list USB drives: {exc}")


class RunWorker(QThread):
    stage = Signal(str)
    progress = Signal(float)
    download = Signal(str)
    confirm_request = Signal(str, str, object)  # title, text, reply holder
    succeeded = Signal(object)  # workflow.Result
    failed = Signal(str, bool)  # message, usb_was_modified
    cancelled = Signal(str)

    def __init__(self, workflow_factory, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.cancel_event = threading.Event()
        self.workflow: Workflow = workflow_factory(self, self.cancel_event)

    def confirm(self, title: str, text: str) -> bool:
        reply = {"answer": False, "event": threading.Event()}
        self.confirm_request.emit(title, text, reply)
        while not reply["event"].wait(0.2):
            if self.cancel_event.is_set():
                return False
        return bool(reply["answer"])

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            result = self.workflow.run()
            self.succeeded.emit(result)
        except CancelledError as exc:
            self.cancelled.emit(str(exc))
        except CorexError as exc:
            log.error("Workflow failed: %s", exc, exc_info=True)
            self.failed.emit(str(exc), self.workflow.writing)
        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected failure:\n%s", traceback.format_exc())
            self.failed.emit(f"Unexpected error: {exc}. Details are in the log file.", self.workflow.writing)


class WorkerUI:
    """Adapts RunWorker signals to the workflow.UI protocol."""

    def __init__(self, worker: RunWorker) -> None:
        self.w = worker

    def stage(self, text: str) -> None:
        self.w.stage.emit(text)

    def progress(self, percent: float) -> None:
        self.w.progress.emit(float(percent))

    def download_status(self, text: str) -> None:
        self.w.download.emit(text)

    def confirm(self, title: str, text: str) -> bool:
        return self.w.confirm(title, text)
