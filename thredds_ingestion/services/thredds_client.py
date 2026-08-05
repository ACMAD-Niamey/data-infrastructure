"""HTTP existence-check and download against a THREDDS fileServer.

Never enumerate/scrape the THREDDS catalog listing (it interleaves dozens of
unrelated products plus .png/.nc previews) - always construct the exact
expected URL from a workflow's patterns and check it directly.
"""

from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

log = logging.getLogger(__name__)


class _LegacyDHAdapter(HTTPAdapter):
    """Accepts TLS servers using a Diffie-Hellman key OpenSSL's default
    security level (SECLEVEL=2) rejects as too small. Only ever used as a
    fallback after a normal request hits that specific error - never applied
    proactively, so any host that doesn't need it keeps the stricter default.
    """

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = create_urllib3_context(ciphers="DEFAULT:@SECLEVEL=1")
        return super().init_poolmanager(*args, **kwargs)


_legacy_tls_session = requests.Session()
_legacy_tls_session.mount("https://", _LegacyDHAdapter())


def _is_weak_dh_error(exc: Exception) -> bool:
    return "DH_KEY_TOO_SMALL" in str(exc)


def _request(method: str, url: str, **kwargs) -> requests.Response:
    try:
        return requests.request(method, url, **kwargs)
    except requests.exceptions.SSLError as exc:
        if not _is_weak_dh_error(exc):
            raise
        log.warning("Retrying %s with relaxed TLS (SECLEVEL=1) - weak DH key: %s", url, exc)
        return _legacy_tls_session.request(method, url, **kwargs)


def exists(url: str, *, timeout: int) -> bool:
    r = _request("HEAD", url, timeout=timeout, allow_redirects=True)
    if r.status_code == 200:
        return True
    if r.status_code == 404:
        return False
    # Some THREDDS fileServer deployments reject HEAD (405) - fall back to a
    # streamed GET and close without reading the body.
    r2 = _request("GET", url, timeout=timeout, stream=True)
    try:
        return r2.status_code == 200
    finally:
        r2.close()


def download_to_path(url: str, dest_path: str, *, timeout: int) -> None:
    r = _request("GET", url, timeout=timeout, stream=True)
    try:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    finally:
        r.close()
