"""STAC and MinIO operations for ingest/delete."""

from __future__ import annotations

import logging
import os
from typing import Any

import botocore.exceptions
import requests

from .datetime_ranges import interval_from_payload
from .storage import s3_client

log = logging.getLogger(__name__)


def stac_base() -> str:
    return os.getenv("STAC_API_URL", "http://stac_api:8080").rstrip("/")


def derive_item_id(
    dataset_id: str,
    *,
    item_id: str | None = None,
    datetime: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
) -> str:
    """Match ingest ``build_item`` id generation."""
    if item_id:
        return item_id
    dt = datetime or start_datetime
    if not dt:
        raise ValueError("item_id or datetime is required")
    return f"{dataset_id}_{dt}".replace(":", "").replace("+", "")


def parse_s3_href(href: str) -> tuple[str, str]:
    if not href or not href.startswith("s3://"):
        raise ValueError(f"asset href must be s3://bucket/key, got {href!r}")
    _, _, rest = href.partition("s3://")
    bucket, _, key = rest.partition("/")
    if not bucket or not key:
        raise ValueError(f"asset href must look like s3://bucket/path, got {href!r}")
    return bucket, key


def get_stac_item(collection_id: str, item_id: str) -> dict[str, Any]:
    url = f"{stac_base()}/collections/{collection_id}/items/{item_id}"
    r = requests.get(url, timeout=25)
    if r.status_code == 404:
        raise ValueError(f"STAC item not found: {collection_id}/{item_id}")
    r.raise_for_status()
    return r.json()


def delete_stac_item(collection_id: str, item_id: str) -> None:
    url = f"{stac_base()}/collections/{collection_id}/items/{item_id}"
    r = requests.delete(url, timeout=25)
    if r.status_code == 404:
        raise ValueError(f"STAC item not found: {collection_id}/{item_id}")
    if r.status_code >= 400:
        raise RuntimeError(f"STAC item DELETE failed {r.status_code}: {r.text}")


def search_stac_items(collection_id: str, start: str, end: str, *, limit: int = 100) -> list[dict[str, Any]]:
    url = f"{stac_base()}/collections/{collection_id}/items"
    params = {"datetime": f"{start}/{end}", "limit": limit}
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json().get("features", [])


def resolve_item_ids_for_delete(dataset_id: str, cadence: str, payload: dict) -> list[str]:
    """
    Resolve one or more STAC item ids to delete.

    Uses explicit ``item_id`` or STAC search by cadence datetime interval.
    """
    explicit = payload.get("item_id")
    if explicit:
        return [explicit]

    start, end = interval_from_payload(cadence, payload)
    features = search_stac_items(dataset_id, start, end)
    return [f["id"] for f in features if f.get("id")]


def data_asset_href(item: dict[str, Any]) -> str | None:
    assets = item.get("assets") or {}
    data = assets.get("data") or {}
    return data.get("href")


def delete_minio_object(href: str) -> None:
    bucket, key = parse_s3_href(href)
    client = s3_client()
    try:
        client.delete_object(Bucket=bucket, Key=key)
        log.info("Deleted MinIO object s3://%s/%s", bucket, key)
    except botocore.exceptions.ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            log.info("MinIO object already absent s3://%s/%s", bucket, key)
            return
        raise
