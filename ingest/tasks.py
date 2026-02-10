import os
import boto3
from celery import shared_task
from botocore.client import Config
import requests
from datetime import datetime, timezone
import botocore
from typing import Optional

from .models import IngestionRun


def s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("MINIO_ROOT_USER", ""),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD", ""),
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

def stac_base():
    # use nginx path if you added /stac/ routing, otherwise http://stac_api:8080
    return os.getenv("STAC_API_URL", "http://stac_api:8080").rstrip("/")

def ensure_collection(collection_id: str, title: Optional[str] = None):
    base = stac_base()
    r = requests.get(f"{base}/collections/{collection_id}", timeout=15)
    if r.status_code == 200:
        return
    if r.status_code != 404:
        r.raise_for_status()

    # Minimal STAC Collection (expand later)
    payload = {
        "id": collection_id,
        "type": "Collection",
        "title": title or collection_id,
        "description": title or collection_id,
        "links": [],
        "license": "CC-BY-4.0",
        "extent": {
            "spatial": {"bbox": [[-180.0, -90.0, 180.0, 90.0]]},
            "temporal": {"interval": [[None, None]]},
        },
    }
    rc = requests.post(f"{base}/collections", json=payload, timeout=20)
    if rc.status_code == 409:
        return
    rc.raise_for_status()

def build_item(dataset_id: str, payload: dict):
    # prefer full stac_item if provided
    if isinstance(payload.get("stac_item"), dict):
        return payload["stac_item"]

    # otherwise build a minimal Feature
    asset = payload.get("asset") or {}
    href = asset.get("href")

    bbox = payload.get("bbox")
    geometry = payload.get("geometry")
    if not bbox or not geometry:
        raise ValueError("Provide bbox and geometry, or provide stac_item")

    # datetime handling: for dekadal/seasonal use start/end
    dt = payload.get("datetime")
    start_dt = payload.get("start_datetime")
    end_dt = payload.get("end_datetime")

    props = {}
    if dt:
        props["datetime"] = dt
    else:
        props["start_datetime"] = start_dt
        props["end_datetime"] = end_dt
        props["datetime"] = start_dt  # some clients expect datetime; ok as start

    item_id = payload.get("item_id") or f"{dataset_id}_{props.get('datetime','')}".replace(":", "").replace("+", "")

    return {
        "stac_version": "1.0.0",
        "id": item_id,
        "type": "Feature",
        "collection": dataset_id,
        "bbox": bbox,
        "geometry": geometry,
        "properties": props,
        "links": [],
        "assets": {
            "data": {
                "href": href,
                "roles": ["data"],
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            }
        },
    }

def post_item(item: dict):
    base = stac_base()
    cid = item["collection"]
    url = f"{base}/collections/{cid}/items"

    r = requests.post(url, json=item, timeout=25)
    if r.status_code >= 400:
        raise RuntimeError(f"STAC item POST failed {r.status_code}: {r.text}")
    return r.json() if r.content else None


@shared_task
def process_ingestion_run(run_id: int):
    run = IngestionRun.objects.get(id=run_id)
    run.status = "processing"
    run.save(update_fields=["status", "updated_at"])

    try:
        payload = run.payload or {}
        asset = payload.get("asset") or {}
        href = asset.get("href", "")

        # For step 5 we validate only s3://bucket/key format
        if not href.startswith("s3://"):
            raise ValueError("asset.href must be an s3://bucket/key URI for MinIO validation in Step 5")

        _, _, rest = href.partition("s3://")
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            raise ValueError("asset.href must look like s3://bucket/path/to/file.tif")

        client = s3_client()

        # create bucket if missing (dev-friendly)
        try:
            client.head_bucket(Bucket=bucket)
        except botocore.exceptions.ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchBucket", "NotFound"):
                client.create_bucket(Bucket=bucket)
            else:
                raise

        client.head_object(Bucket=bucket, Key=key)

        # ensure collection exists
        ensure_collection(run.dataset_id, title=run.dataset_id)

        # build and post item
        item = build_item(run.dataset_id, payload)
        post_item(item)


        # If we got here, object exists
        run.status = "completed"
        run.save(update_fields=["status", "updated_at"])
        return {"ok": True, "bucket": bucket, "key": key}

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.save(update_fields=["status", "error_message", "updated_at"])
        return {"ok": False, "error": str(e)}
1