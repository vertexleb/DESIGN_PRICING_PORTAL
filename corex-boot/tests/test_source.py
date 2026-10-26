"""Official-page parsing. The fixture mimics the layout of hirensbootcd.org/download;
values are synthetic, not real Hiren's checksums."""

import pytest

from corex_boot.errors import SourceError
from corex_boot.source import discover_release, is_official_url, parse_download_page

SHA256 = "a" * 64
SHA1 = "b" * 40
MD5 = "c" * 32

PAGE = f"""
<html><body>
<h2>Hiren's BootCD PE x64 (v9.9.9)</h2>
<table>
<tr><td>Filename:</td><td>HBCD_PE_x64.iso</td></tr>
<tr><td>Size:</td><td>3.08 GB</td></tr>
<tr><td>MD5:</td><td>{MD5.upper()}</td></tr>
<tr><td>SHA-1:</td><td>{SHA1.upper()}</td></tr>
<tr><td>SHA-256:</td><td>{SHA256.upper()}</td></tr>
</table>
<a href="/files/HBCD_PE_x64.iso">Download ISO</a>
<a href="https://mirror.example.com/HBCD_PE_x64.iso">Mirror</a>
</body></html>
"""


def test_parses_url_and_checksums():
    r = parse_download_page(PAGE)
    assert r.url == "https://www.hirensbootcd.org/files/HBCD_PE_x64.iso"
    assert r.filename == "HBCD_PE_x64.iso"
    assert r.version == "9.9.9"
    assert r.size_text == "3.08 GB"
    assert r.checksums == {"sha256": SHA256, "sha1": SHA1, "md5": MD5}
    assert r.best_checksum == ("sha256", SHA256)


def test_unofficial_mirror_links_are_ignored():
    page = '<a href="https://mirror.example.com/HBCD_PE_x64.iso">x</a>'
    with pytest.raises(SourceError, match="outside hirensbootcd.org"):
        parse_download_page(page)


def test_plain_http_link_rejected():
    page = '<a href="http://www.hirensbootcd.org/files/HBCD_PE_x64.iso">x</a>'
    with pytest.raises(SourceError):
        parse_download_page(page)


def test_lookalike_domain_rejected():
    assert not is_official_url("https://hirensbootcd.org.evil.com/x.iso")
    assert not is_official_url("https://evilhirensbootcd.org/x.iso")
    assert is_official_url("https://www.hirensbootcd.org/x.iso")
    assert is_official_url("https://hirensbootcd.org/x.iso")


def test_no_checksum_published_means_unverifiable():
    r = parse_download_page('<a href="/files/HBCD_PE_x64.iso">x</a>')
    assert r.best_checksum is None


def test_conflicting_checksums_are_not_used():
    page = f'<a href="/files/HBCD_PE_x64.iso">x</a><p>SHA-256: {"1"*64}</p><p>SHA-256: {"2"*64}</p><p>SHA1: {SHA1}</p>'
    r = parse_download_page(page)
    assert "sha256" not in r.checksums
    assert r.best_checksum == ("sha1", SHA1)


def test_prefers_x64_iso_when_several():
    page = '<a href="/files/HBCD_PE_x64.iso">a</a><a href="/files/Other.iso">b</a>'
    assert parse_download_page(page).filename == "HBCD_PE_x64.iso"


def test_ambiguous_iso_links_refused():
    page = '<a href="/files/A.iso">a</a><a href="/files/B.iso">b</a>'
    with pytest.raises(SourceError, match="several ISO"):
        parse_download_page(page)


def test_no_iso_link():
    with pytest.raises(SourceError):
        parse_download_page("<html>maintenance</html>")


class _Resp:
    def __init__(self, url, body):
        self._url, self._body = url, body
        import email.message
        self.headers = email.message.Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"

    def geturl(self):
        return self._url

    def read(self, n=-1):
        return self._body.encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_discover_release_uses_official_page():
    seen = []

    def opener(url):
        seen.append(url)
        return _Resp(url, PAGE)

    r = discover_release(opener)
    assert seen == ["https://www.hirensbootcd.org/download/"]
    assert r.best_checksum == ("sha256", SHA256)


def test_discover_release_network_failure():
    def opener(url):
        raise OSError("no network")

    with pytest.raises(SourceError, match="Could not reach"):
        discover_release(opener)


def test_discover_release_redirect_off_domain():
    with pytest.raises(SourceError, match="unexpected address"):
        discover_release(lambda url: _Resp("https://evil.example/download/", PAGE))
