"""Runs the bundled PowerShell scripts (Windows built-in Storage cmdlets) and parses JSON output."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .errors import PermissionDeniedError, PowerShellError

log = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000


def scripts_dir() -> Path:
    # PyInstaller one-file bundles extract data files under sys._MEIPASS.
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "corex_boot" / "scripts"
    return Path(__file__).resolve().parent / "scripts"


def powershell_exe() -> str:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(candidate) if candidate.exists() else "powershell.exe"


def run_script(name: str, args: dict[str, Any] | None = None, timeout: float = 600) -> Any:
    """Run scripts/<name>.ps1 with named parameters; return parsed JSON from stdout."""
    script = scripts_dir() / f"{name}.ps1"
    cmd = [
        powershell_exe(), "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-File", str(script),
    ]
    for key, value in (args or {}).items():
        cmd += [f"-{key}", str(value)]
    log.debug("PowerShell: %s %s", name, args)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
            creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except FileNotFoundError as exc:
        raise PowerShellError("Windows PowerShell was not found on this computer.") from exc
    except subprocess.TimeoutExpired as exc:
        raise PowerShellError(f"A Windows disk operation ({name}) timed out.") from exc

    stdout, stderr = proc.stdout.strip(), proc.stderr.strip()
    log.debug("PowerShell %s exit=%s stdout=%s stderr=%s", name, proc.returncode, stdout[-4000:], stderr[-4000:])
    if proc.returncode != 0:
        detail = _first_error_line(stderr) or _first_error_line(stdout) or "unknown error"
        if "access is denied" in detail.lower() or "access denied" in detail.lower():
            raise PermissionDeniedError(
                "Windows denied access to the disk. Please run Corex Boot as Administrator."
            )
        raise PowerShellError(detail)
    # Scripts print exactly one JSON document as their last stdout line.
    last = stdout.splitlines()[-1] if stdout else ""
    try:
        return json.loads(last) if last else None
    except json.JSONDecodeError as exc:
        raise PowerShellError(f"Unexpected output from {name}: {last[:200]}") from exc


def _first_error_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("COREX_ERROR:"):
            return line.removeprefix("COREX_ERROR:").strip()
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""
