"""Discovers the current official Hiren's BootCD PE ISO URL and published checksums.

Nothing is hardcoded: the official download page is fetched and parsed at runtime.
If the page publishes no single, unambiguous checksum, the release is marked
unverifiable and the caller must tell the user."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from . import config
from .errors import SourceError
from .net import open_url

log = logging.getLogger(__name__)

# Strongest first. The app verifies with the strongest one the page publishes.
HASH_ALGORITHMS = (("sha256", 64, r"SHA[-\s]?256"), ("sha1", 40, r"SHA[-\s]?1(?!\d)"), ("md5", 32, r"MD5"))


@dataclass(frozen=True)
class IsoRelease:
    url: str
    filename: str
    version: str | None
    checksums: dict[str, str] = field(default_factory=dict)
    size_text: str | None = None

    @property
    def best_checksum(self) -> tuple[str, str] | None:
        for algo, _, _ in HASH_ALGORITHMS:
            if algo in self.checksums:
                return algo, self.checksums[algo]
        return None


def is_official_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in config.OFFICIAL_DOMAINS)


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href.strip())
        if tag in ("br", "p", "div", "tr", "li", "td", "th", "h1", "h2", "h3", "h4", "table"):
            self.text.append("\n")

    def handle_data(self, data):
        self.text.append(data)


def parse_download_page(html: str, page_url: str = config.OFFICIAL_DOWNLOAD_PAGE) -> IsoRelease:
    parser = _PageParser()
    parser.feed(html)
    text = "".join(parser.text)

    iso_links = []
    for href in parser.links:
        absolute = urljoin(page_url, href)
        if urlparse(absolute).path.lower().endswith(".iso"):
            if absolute not in iso_links:
                iso_links.append(absolute)
    official = [u for u in iso_links if is_official_url(u)]
    rejected = [u for u in iso_links if u not in official]
    if rejected:
        log.warning("Ignoring non-official or non-HTTPS ISO links: %s", rejected)
    if not official and rejected:
        raise SourceError(
            "The official Hiren's BootCD page points to a download address outside hirensbootcd.org "
            f"({rejected[0]}). For safety Corex Boot only downloads over HTTPS from hirensbootcd.org. "
            "Download the ISO manually from https://www.hirensbootcd.org/download/ if you trust that address."
        )
    if not official:
        raise SourceError(
            "Could not find the ISO download link on the official Hiren's BootCD website. "
            "The page layout may have changed; please check https://www.hirensbootcd.org/download/."
        )
    # Prefer the 64-bit PE build when several ISOs are offered.
    preferred = [u for u in official if "x64" in u.lower()] or official
    if len(preferred) > 1:
        raise SourceError(
            "The official download page lists several ISO files and the correct one could not be "
            "determined automatically: " + ", ".join(preferred)
        )
    url = preferred[0]
    filename = urlparse(url).path.rsplit("/", 1)[-1]

    checksums: dict[str, str] = {}
    for algo, length, label in HASH_ALGORITHMS:
        pattern = re.compile(label + r"[^0-9A-Za-z]{0,20}([0-9A-Fa-f]{%d})(?![0-9A-Fa-f])" % length, re.I)
        values = {m.group(1).lower() for m in pattern.finditer(text)}
        if len(values) == 1:
            checksums[algo] = values.pop()
        elif len(values) > 1:
            log.warning("Page lists %d different %s values; not using %s", len(values), algo, algo)

    version = None
    m = re.search(r"\bv(?:ersion)?\s*[:.]?\s*(\d+\.\d+(?:\.\d+)*)", text, re.I)
    if m:
        version = m.group(1)
    size_text = None
    m = re.search(r"Size[^0-9]{0,20}(\d+(?:[.,]\d+)?\s*(?:GB|MB))\b", text, re.I)
    if m:
        size_text = m.group(1)

    release = IsoRelease(url=url, filename=filename, version=version, checksums=checksums, size_text=size_text)
    log.info("Discovered release: %s", release)
    return release


def discover_release(opener=open_url) -> IsoRelease:
    try:
        with opener(config.OFFICIAL_DOWNLOAD_PAGE) as resp:
            final = resp.geturl()
            if not is_official_url(final):
                raise SourceError(f"The official download page redirected to an unexpected address: {final}")
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read(5 * 1024 * 1024).decode(charset, errors="replace")
    except SourceError:
        raise
    except Exception as exc:
        log.exception("Could not read official download page")
        raise SourceError(
            "Could not reach the official Hiren's BootCD website (hirensbootcd.org). "
            "Check the internet connection and try again."
        ) from exc
    return parse_download_page(html, final)
