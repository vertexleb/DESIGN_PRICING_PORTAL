"""Download resume/interrupt behaviour against a real local HTTP server."""

import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from corex_boot.downloader import Downloader
from corex_boot.errors import CancelledError, DownloadError, InsufficientCapacityError

DATA = bytes(range(256)) * 4096 * 3  # 3 MiB


class Server:
    def __init__(self):
        self.drop_after = None  # drop connection after N bytes (once)
        self.ignore_range = False
        self.redirect_to = None
        self.status = None
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                outer.requests.append(dict(self.headers))
                if outer.status:
                    self.send_error(outer.status)
                    return
                if outer.redirect_to:
                    self.send_response(302)
                    self.send_header("Location", outer.redirect_to)
                    self.end_headers()
                    return
                start = 0
                rng = self.headers.get("Range")
                if rng and not outer.ignore_range:
                    start = int(rng.split("=")[1].split("-")[0])
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{len(DATA)-1}/{len(DATA)}")
                else:
                    self.send_response(200)
                body = DATA[start:]
                self.send_header("Content-Length", str(len(body)))
                self.send_header("ETag", '"v1"')
                self.end_headers()
                if outer.drop_after is not None:
                    n, outer.drop_after = outer.drop_after, None
                    self.wfile.write(body[:n])
                    self.wfile.flush()
                    self.connection.shutdown(2)
                    return
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/files/HBCD_PE_x64.iso"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()


@pytest.fixture
def server():
    s = Server()
    yield s
    s.httpd.shutdown()


def local_only(url):
    return url.startswith("http://127.0.0.1")


def make(server, tmp_cache, **kw):
    return Downloader(server.url, tmp_cache / "HBCD_PE_x64.iso", allow=local_only, retry_delay=0.01, **kw)


def test_full_download(server, tmp_cache):
    seen = []
    path = make(server, tmp_cache, progress=lambda d, t, s: seen.append((d, t))).run()
    assert path.read_bytes() == DATA
    assert seen[-1] == (len(DATA), len(DATA))
    assert not path.with_name(path.name + ".part").exists()


def test_interrupted_download_resumes_with_range(server, tmp_cache):
    server.drop_after = 1_000_000
    path = make(server, tmp_cache).run()
    assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(DATA).digest()
    assert server.requests[1]["Range"].startswith("bytes=")
    assert int(server.requests[1]["Range"][6:-1]) > 0
    assert server.requests[1]["If-Range"] == '"v1"'


def test_resume_across_program_restart(server, tmp_cache):
    server.drop_after = 500_000
    first = make(server, tmp_cache, max_retries=0)
    with pytest.raises(DownloadError, match="interrupted"):
        first.run()
    part = tmp_cache / "HBCD_PE_x64.iso.part"
    assert part.exists() and 0 < part.stat().st_size < len(DATA)
    path = make(server, tmp_cache).run()  # "next launch"
    assert path.read_bytes() == DATA
    assert "Range" in server.requests[-1]


def test_server_ignoring_range_restarts_cleanly(server, tmp_cache):
    server.drop_after = 700_000
    server.ignore_range = True
    path = make(server, tmp_cache).run()
    assert path.read_bytes() == DATA


def test_completed_download_is_reused(server, tmp_cache):
    make(server, tmp_cache).run()
    n = len(server.requests)
    make(server, tmp_cache).run()
    assert len(server.requests) == n


def test_new_release_url_discards_old_partial(server, tmp_cache):
    (tmp_cache / "HBCD_PE_x64.iso.part").write_bytes(b"x" * 100)
    (tmp_cache / "HBCD_PE_x64.iso.json").write_text('{"url": "http://127.0.0.1/old.iso"}')
    path = make(server, tmp_cache).run()
    assert path.read_bytes() == DATA
    assert "Range" not in server.requests[0]


def test_redirect_to_unofficial_host_blocked(server, tmp_cache):
    server.redirect_to = "https://mirror.example.com/HBCD_PE_x64.iso"
    with pytest.raises(DownloadError, match="non-official"):
        make(server, tmp_cache).run()


def test_non_official_url_refused_before_connecting(tmp_cache):
    d = Downloader("http://www.hirensbootcd.org/files/x.iso", tmp_cache / "x.iso")
    with pytest.raises(DownloadError, match="non-official or non-HTTPS"):
        d.run()


def test_http_404_is_not_retried(server, tmp_cache):
    server.status = 404
    with pytest.raises(DownloadError, match="HTTP 404"):
        make(server, tmp_cache).run()
    assert len(server.requests) == 1


def test_cancel_keeps_partial_for_resume(server, tmp_cache):
    cancel = threading.Event()

    def progress(done, total, speed):
        if done > 1_000_000:
            cancel.set()

    with pytest.raises(CancelledError):
        make(server, tmp_cache, progress=progress, cancel=cancel).run()
    assert (tmp_cache / "HBCD_PE_x64.iso.part").exists()


def test_insufficient_usb_capacity_aborts_download_early(server, tmp_cache):
    def on_total(total):
        raise InsufficientCapacityError("USB too small")

    with pytest.raises(InsufficientCapacityError):
        make(server, tmp_cache, on_total=on_total).run()
    assert len(server.requests) == 1
