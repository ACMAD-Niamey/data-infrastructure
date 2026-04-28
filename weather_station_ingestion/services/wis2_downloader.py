from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings


@dataclass
class DownloadResult:
    url: str
    status_code: int
    content: bytes
    content_type: str | None
    content_length: int
    local_file_path: str | None = None


class WIS2Downloader:
    def _build_local_path(self, url: str) -> Path:
        parsed = urlparse(url)
        filename = Path(parsed.path).name or "payload.bin"
        target_dir = Path(settings.WIS2_DOWNLOAD_DIR)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    def _save_file(self, url: str, content: bytes) -> str:
        path = self._build_local_path(url)
        path.write_bytes(content)
        return str(path)

    def download(self, url: str) -> DownloadResult:
        response = requests.get(url, timeout=settings.WIS2_DOWNLOAD_TIMEOUT)
        response.raise_for_status()

        content = response.content
        local_file_path = None

        if settings.WIS2_KEEP_DOWNLOADED_FILES:
            local_file_path = self._save_file(url, content)

        return DownloadResult(
            url=url,
            status_code=response.status_code,
            content=content,
            content_type=response.headers.get("Content-Type"),
            content_length=len(content),
            local_file_path=local_file_path,
        )