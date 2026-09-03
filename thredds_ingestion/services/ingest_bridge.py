"""Bridge into the existing upload/ingest pipeline, without going over HTTP.

DirectUpFileUploadView requires interactive session/basic auth and exists for
browser/API clients; everything it does under auto_ingest=True (MinIO put +
IngestionRun create + process_ingestion_run) is directly importable Python
from within the same process. A Celery task in this app calls those pieces
directly instead of round-tripping through DRF and faking auth for no reason.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime

import botocore.exceptions

from ingest.storage import set_bucket_public
from uploads.storage.minio import minio_client

log = logging.getLogger(__name__)

DEFAULT_BUCKET = os.getenv("MINIO_DEFAULT_BUCKET", "geodata")


def build_minio_key(collection: str, run_date: date, filename: str) -> str:
    """Deterministic key, no UUID - a retry overwrites the same object instead
    of creating an orphaned duplicate blob, since filename is already unique
    per (workflow_file, run_date, lead_hours) by construction. Prefixed by the
    STAC collection so multiple sources under one dataset don't collide."""
    return f"{collection}/{run_date:%Y/%m}/{filename}"


def upload_file(local_path: str, *, bucket: str = DEFAULT_BUCKET, key: str, content_type: str = "image/tiff") -> str:
    """Put local_path to MinIO at bucket/key, creating the bucket if missing. Returns the s3:// href."""
    client = minio_client()
    try:
        client.head_bucket(Bucket=bucket)
    except botocore.exceptions.ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket", "NotFound"):
            client.create_bucket(Bucket=bucket)
            set_bucket_public(client, bucket)
        else:
            raise

    with open(local_path, "rb") as fh:
        client.put_object(Bucket=bucket, Key=key, Body=fh, ContentType=content_type)
    return f"s3://{bucket}/{key}"


def push_to_ingest(
    *,
    collection: str,
    cadence: str,
    href: str,
    item_id: str,
    valid_datetime: datetime,
    valid_end_datetime: datetime | None = None,
):
    """Create an IngestionRun for href and run it synchronously (not .delay()),
    so the final status is known immediately with no polling. Reuses
    ingest.tasks.process_ingestion_run, which already does COG conversion and
    bbox/geometry extraction internally - nothing here duplicates that.

    valid_end_datetime is None for point-in-time items (the common case) -
    ingest.tasks.build_item is told a single `datetime`. When set (a
    workflow_file with validity_hours configured), it's a window instead -
    build_item is told `start_datetime`/`end_datetime`, matching how
    dekadal/seasonal cadence items are already expressed by the ingest API.
    """
    from ingest.models import IngestionRun
    from ingest.tasks import process_ingestion_run

    payload = {"item_id": item_id, "asset": {"href": href}}
    if valid_end_datetime is not None:
        payload["start_datetime"] = valid_datetime.isoformat()
        payload["end_datetime"] = valid_end_datetime.isoformat()
    else:
        payload["datetime"] = valid_datetime.isoformat()

    # IngestionRun.dataset_id is used downstream verbatim as the STAC collection
    # id (ingest.tasks.ensure_collection/build_item), so it carries the resolved
    # collection here, which may be a per-layer collection rather than a dataset_id.
    run = IngestionRun.objects.create(
        dataset_id=collection,
        cadence=cadence,
        status="accepted",
        payload=payload,
    )
    process_ingestion_run(run.id)
    run.refresh_from_db()
    return run
