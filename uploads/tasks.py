import logging
import os
import json

from celery import shared_task
from django.core.cache import cache

from .storage.minio import minio_client
from catalog.models import DatasetPage
from ingest.models import IngestionRun
from ingest.tasks import process_ingestion_run


logger = logging.getLogger(__name__)


def _set_bucket_public(client, bucket: str):
    """
    Set bucket policy to allow public read access (download only).
    This allows files to be accessed via HTTP without authentication.
    """
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"]
            }
        ]
    }
    
    try:
        client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        logger.info(f"Set bucket {bucket} to public read access")
    except Exception as e:
        logger.warning(f"Failed to set public policy on bucket {bucket}: {e}")


def _extract_raster_bbox_geometry(file_path: str):
    try:
        from osgeo import gdal, osr
    except Exception as e:
        raise RuntimeError(f"GDAL import failed: {e}")

    dataset = gdal.Open(file_path)
    if dataset is None:
        raise RuntimeError("GDAL could not open raster")

    geotransform = dataset.GetGeoTransform()
    if not geotransform:
        raise RuntimeError("Missing geotransform")

    x_min = geotransform[0]
    y_max = geotransform[3]
    x_res = geotransform[1]
    y_res = geotransform[5]

    x_max = x_min + (dataset.RasterXSize * x_res)
    y_min = y_max + (dataset.RasterYSize * y_res)

    source_srs = osr.SpatialReference()
    source_wkt = dataset.GetProjection()
    if source_wkt:
        source_srs.ImportFromWkt(source_wkt)
    else:
        source_srs.ImportFromEPSG(4326)

    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)

    if source_srs.IsSame(target_srs):
        bbox = [x_min, y_min, x_max, y_max]
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [x_min, y_min],
                [x_min, y_max],
                [x_max, y_max],
                [x_max, y_min],
                [x_min, y_min],
            ]],
        }
        return bbox, geometry

    transform = osr.CoordinateTransformation(source_srs, target_srs)
    corners = [
        (x_min, y_min),
        (x_min, y_max),
        (x_max, y_max),
        (x_max, y_min),
    ]
    transformed = [transform.TransformPoint(x, y) for x, y in corners]
    xs = [pt[0] for pt in transformed]
    ys = [pt[1] for pt in transformed]
    bbox = [min(xs), min(ys), max(xs), max(ys)]
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [xs[0], ys[0]],
            [xs[1], ys[1]],
            [xs[2], ys[2]],
            [xs[3], ys[3]],
            [xs[0], ys[0]],
        ]],
    }
    return bbox, geometry

@shared_task(bind=True)
def upload_file_to_minio(
    self,
    file_path: str,
    bucket: str,
    key: str,
    content_type: str,
    task_key: str,
    dataset_id: str,
    auto_ingest: bool,
    ingest_payload: dict | None,
    auto_extract: bool,
):
    """
    Upload file to MinIO in the background.
    Updates cache with progress status.
    """
    logger.info("Starting upload task for %s to s3://%s/%s", file_path, bucket, key)

    try:
        cache.set(
            task_key,
            {
                "status": "processing",
                "bucket": bucket,
                "key": key,
                "auto_ingest": auto_ingest,
                "error": None,
            },
            timeout=3600,
        )
        logger.info("Status updated to processing for task %s", task_key)

        client = minio_client()
        logger.info("MinIO client created successfully")

        try:
            client.head_bucket(Bucket=bucket)
            logger.info("Bucket %s exists", bucket)
        except Exception as e:
            logger.info("Creating bucket %s: %s", bucket, e)
            client.create_bucket(Bucket=bucket)
            # Set bucket to public read access
            _set_bucket_public(client, bucket)

        file_size = os.path.getsize(file_path)
        logger.info("Uploading file %s (%s bytes)", file_path, file_size)
        with open(file_path, "rb") as file_handle:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_handle,
                ContentType=content_type,
            )

        href = f"s3://{bucket}/{key}"
        logger.info("Upload completed: %s", href)

        status_payload = {
            "status": "completed",
            "bucket": bucket,
            "key": key,
            "href": href,
            "size": file_size,
            "content_type": content_type,
            "auto_ingest": auto_ingest,
            "error": None,
        }

        if auto_ingest:
            ingest_status = "accepted"
            ingest_run_id = None
            ingest_error = None

            dataset = DatasetPage.objects.filter(dataset_id=dataset_id).first()
            if not dataset:
                ingest_status = "failed"
                ingest_error = f"Unknown dataset_id '{dataset_id}'"
            else:
                payload = ingest_payload.copy() if ingest_payload else {}
                stac_item = payload.get("stac_item")
                if stac_item:
                    stac_item.setdefault("assets", {})
                    stac_item["assets"].setdefault("data", {})
                    stac_item["assets"]["data"]["href"] = href
                    payload["stac_item"] = stac_item
                else:
                    if auto_extract and (not payload.get("bbox") or not payload.get("geometry")):
                        try:
                            bbox, geometry = _extract_raster_bbox_geometry(file_path)
                            payload["bbox"] = bbox
                            payload["geometry"] = geometry
                            logger.info("Extracted raster bbox/geometry via GDAL")
                        except Exception as e:
                            ingest_status = "failed"
                            ingest_error = f"GDAL extraction failed: {e}"

                    if ingest_status == "failed":
                        status_payload.update(
                            {
                                "ingest_status": ingest_status,
                                "ingest_run_id": ingest_run_id,
                                "ingest_error": ingest_error,
                            }
                        )
                        cache.set(task_key, status_payload, timeout=3600)
                        return status_payload

                    payload["asset"] = {"href": href}

                run = IngestionRun.objects.create(
                    dataset_id=dataset.dataset_id,
                    cadence=dataset.cadence,
                    status="accepted",
                    payload=payload,
                )
                process_ingestion_run.delay(run.id)
                ingest_run_id = run.id

            status_payload.update(
                {
                    "ingest_status": ingest_status,
                    "ingest_run_id": ingest_run_id,
                    "ingest_error": ingest_error,
                }
            )

        cache.set(task_key, status_payload, timeout=3600)
        logger.info("Status updated to completed for task %s", task_key)

        try:
            os.remove(file_path)
            logger.info("Cleaned up temp file: %s", file_path)
        except Exception as e:
            logger.warning("Failed to clean up temp file: %s", e)

        return {"status": "completed", "href": href}

    except Exception as e:
        logger.error("Upload task failed: %s", str(e), exc_info=True)
        cache.set(
            task_key,
            {
                "status": "failed",
                "bucket": bucket,
                "key": key,
                "auto_ingest": auto_ingest,
                "error": str(e),
            },
            timeout=3600,
        )

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        raise
