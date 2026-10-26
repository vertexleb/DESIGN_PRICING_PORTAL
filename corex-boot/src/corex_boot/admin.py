"""Administrator privilege detection and UAC re-launch."""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys

log = logging.getLogger(__name__)


def is_admin() -> bool:
    if os.name != "nt":
        return hasattr(os, "geteuid") and os.geteuid() == 0
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin() -> bool:
    """Ask UAC to restart this program elevated. Returns True if the elevated copy started."""
    if os.name != "nt":
        return False
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, subprocess.list2cmdline(sys.argv[1:])
    else:
        exe, params = sys.executable, subprocess.list2cmdline(["-m", "corex_boot", *sys.argv[1:]])
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    log.info("UAC relaunch requested, ShellExecuteW returned %s", rc)
    return rc > 32
