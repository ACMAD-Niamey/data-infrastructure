from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class WIS2Notification:
    source_identifier: str | None
    topic: str
    data_id: str | None
    metadata_id: str | None
    canonical_url: str | None
    content_type: str | None
    pubtime: datetime | None
    data_datetime: datetime | None
    global_cache: str | None
    raw_payload: dict[str, Any]


class WIS2NotificationParser:
    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        except Exception:
            return None

    def parse(self, topic: str, payload: dict[str, Any]) -> WIS2Notification:
        props = payload.get("properties", {}) or {}
        links = payload.get("links", []) or []
        canonical_link = next((l for l in links if l.get("rel") == "canonical"), None)

        return WIS2Notification(
            source_identifier=payload.get("id"),
            topic=topic,
            data_id=props.get("data_id"),
            metadata_id=props.get("metadata_id"),
            canonical_url=canonical_link.get("href") if canonical_link else None,
            content_type=canonical_link.get("type") if canonical_link else None,
            pubtime=self._parse_dt(props.get("pubtime")),
            data_datetime=self._parse_dt(props.get("datetime")),
            global_cache=props.get("global-cache"),
            raw_payload=payload,
        )