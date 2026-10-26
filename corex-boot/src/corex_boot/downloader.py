"""Resumable HTTPS downloader (HTTP Range + If-Range) restricted to official hosts."""

from __future__ import annotations

import http.client
import json
import logging
import re
import threading
import time
import urllib.error
from pathlib import Path
from typing import Callable

from . import config
from .errors import CancelledError, DownloadError
from .net import open_url
from .source import is_official_url

log = logging.getLogger(__name__)

ProgressFn = Callable[[int, int | None, float], None]


class Downloader:
    def __init__(
        self,
        url: str,
        dest: Path,
        *,
        progress: ProgressFn | None = None,
        on_total: Callable[[int], None] | None = None,
        cancel: threading.Event | None = None,
        allow: Callable[[str], bool] = is_official_url,
        max_retries: int = 5,
        retry_delay: float = 2.0,
    ) -> None:
        self.url = url
        self.dest = Path(dest)
        self.part = self.dest.with_name(self.dest.name + ".part")
        self.meta = self.dest.with_name(self.dest.name + ".json")
        self.progress = progress or (lambda *_: None)
        self.on_total = on_total or (lambda _: None)
        self.cancel = cancel or threading.Event()
        self.allow = allow
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    # -- metadata -------------------------------------------------------
    def _load_meta(self) -> dict:
        try:
            return json.loads(self.meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_meta(self, meta: dict) -> None:
        self.meta.write_text(json.dumps(meta), encoding="utf-8")

    def discard(self) -> None:
        for path in (self.dest, self.part, self.meta):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    # -- main -----------------------------------------------------------
    def run(self) -> Path:
        if not self.allow(self.url):
            raise DownloadError(f"Refusing to download from a non-official or non-HTTPS address: {self.url}")
        meta = self._load_meta()
        if meta.get("url") != self.url:
            # Different release (or no metadata): never mix bytes from two files.
            self.discard()
            meta = {"url": self.url}
            self._save_meta(meta)
        elif self.dest.exists() and meta.get("complete"):
            log.info("Reusing previously downloaded %s", self.dest)
            size = self.dest.stat().st_size
            self.on_total(size)
            self.progress(size, size, 0.0)
            return self.dest

        attempt = 0
        while True:
            try:
                self._attempt(meta)
                break
            except CancelledError:
                raise
            except DownloadError:
                raise
            except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
                attempt += 1
                log.warning("Download attempt %d failed: %s", attempt, exc)
                if isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500 and exc.code != 416:
                    raise DownloadError(f"The official server refused the download (HTTP {exc.code}).") from exc
                if "blocked redirect" in str(exc) or "refusing non-official" in str(exc):
                    raise DownloadError(
                        "The download was redirected to a non-official address and was stopped for safety."
                    ) from exc
                if attempt > self.max_retries:
                    raise DownloadError(
                        "The download was interrupted repeatedly. Check the internet connection and press "
                        "Start again - the download will resume where it stopped."
                    ) from exc
                self._sleep(self.retry_delay * attempt)

        self.part.replace(self.dest)
        meta["complete"] = True
        self._save_meta(meta)
        return self.dest

    def _sleep(self, seconds: float) -> None:
        if self.cancel.wait(seconds):
            raise CancelledError()

    def _attempt(self, meta: dict) -> None:
        offset = self.part.stat().st_size if self.part.exists() else 0
        headers = {}
        if offset:
            headers["Range"] = f"bytes={offset}-"
            validator = meta.get("etag") or meta.get("last_modified")
            if validator:
                headers["If-Range"] = validator
        try:
            resp = open_url(self.url, headers, allow=self.allow)
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and offset and meta.get("total") == offset:
                log.info("Server reports range not satisfiable; part file already complete")
                return
            if exc.code == 416:
                self.part.unlink(missing_ok=True)
            raise

        with resp:
            if not self.allow(resp.geturl()):
                raise DownloadError("The download was redirected to a non-official address and was stopped.")
            status = resp.status
            if status == 206:
                m = re.match(r"bytes (\d+)-(\d+)/(\d+|\*)", resp.headers.get("Content-Range", ""))
                if not m or int(m.group(1)) != offset:
                    raise DownloadError("The server returned an unexpected byte range; restart the download.")
                total = int(m.group(3)) if m.group(3) != "*" else None
                mode = "ab"
                log.info("Resuming download at byte %d of %s", offset, total)
            elif status == 200:
                if offset:
                    log.info("Server ignored the resume request; restarting from zero")
                offset = 0
                length = resp.headers.get("Content-Length")
                total = int(length) if length and length.isdigit() else None
                mode = "wb"
            else:
                raise DownloadError(f"Unexpected HTTP status {status} from the official server.")

            meta.update(
                etag=resp.headers.get("ETag") if resp.headers.get("ETag", "").startswith('"') else None,
                last_modified=resp.headers.get("Last-Modified"),
                total=total,
            )
            self._save_meta(meta)
            if total:
                self.on_total(total)

            done = offset
            start = time.monotonic()
            received = 0
            with open(self.part, mode) as out:
                while True:
                    if self.cancel.is_set():
                        raise CancelledError("Download paused. Press Start again to resume.")
                    chunk = resp.read(config.DOWNLOAD_CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    received += len(chunk)
                    elapsed = max(time.monotonic() - start, 1e-6)
                    self.progress(done, total, received / elapsed)
            if total is not None and done != total:
                raise ConnectionError(f"connection closed early at {done} of {total} bytes")
            if total is None:
                meta["total"] = done
                self._save_meta(meta)
