from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from . import __version__
from .config import log_dir


def setup_logging(directory: Path | None = None) -> Path:
    directory = directory or log_dir()
    log_file = directory / "corex_boot.log"
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(threadName)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    logging.getLogger(__name__).info("Corex Boot %s starting; log file %s", __version__, log_file)
    return log_file
