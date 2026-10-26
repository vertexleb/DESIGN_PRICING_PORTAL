"""HTTPS opener that refuses to follow redirects off the official domain or to plain HTTP."""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from typing import Callable

from . import config


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allow: Callable[[str], bool]) -> None:
        super().__init__()
        self.allow = allow

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not self.allow(newurl):
            raise urllib.error.URLError(f"blocked redirect to non-official address {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_opener(allow: Callable[[str], bool] | None = None) -> urllib.request.OpenerDirector:
    from .source import is_official_url

    context = ssl.create_default_context()  # verifies certificates; uses the Windows store on Windows
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context),
        _GuardedRedirect(allow or is_official_url),
    )


def open_url(url: str, headers: dict[str, str] | None = None, allow: Callable[[str], bool] | None = None):
    from .source import is_official_url

    check = allow or is_official_url
    if not check(url):
        raise urllib.error.URLError(f"refusing non-official or non-HTTPS address {url}")
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT, **(headers or {})})
    return build_opener(check).open(req, timeout=config.HTTP_TIMEOUT_S)
