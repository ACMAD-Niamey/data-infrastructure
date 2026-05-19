"""Cloud Optimized GeoTIFF conversion for ingest pipeline."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles

log = logging.getLogger(__name__)

_TIFF_SUFFIXES = (".tif", ".tiff")


def is_tiff_key(key: str) -> bool:
    lower = (key or "").lower()
    return lower.endswith(_TIFF_SUFFIXES)


def is_valid_cog(path: str, *, strict: bool = False) -> bool:
    """Return True when the local file is already a valid COG."""
    try:
        valid, _errors, _warnings = cog_validate(path, strict=strict)
        return bool(valid)
    except Exception as exc:
        log.debug("COG validation failed for %s: %s", path, exc)
        return False


def convert_to_cog(src_path: str, dst_path: str, *, resampling: str = "average") -> None:
    """Translate a raster to COG at dst_path."""
    profile = cog_profiles.get("deflate")
    config = {
        "GDAL_NUM_THREADS": "ALL_CPUS",
        "RESAMPLING": resampling,
        "OVERVIEWS": "AUTO",
        "OVERVIEW_RESAMPLING": resampling,
        "BIGTIFF": "IF_SAFER",
    }
    cog_translate(
        src_path,
        dst_path,
        profile,
        config=config,
        in_memory=False,
        quiet=True,
    )


def ensure_raster_is_cog(
    s3_client,
    bucket: str,
    key: str,
    *,
    resampling: str = "average",
) -> dict[str, Any]:
    """
    Ensure the MinIO object at bucket/key is a COG, overwriting the same key in place.

    Returns metadata: optimized (bool), skipped (str|None).
    """
    if not is_tiff_key(key):
        return {"optimized": False, "skipped": "not_tiff"}

    src_path = None
    dst_path = None
    try:
        suffix = os.path.splitext(key)[1] or ".tif"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as src_tmp:
            src_path = src_tmp.name
        s3_client.download_file(bucket, key, src_path)

        if is_valid_cog(src_path):
            log.info("Skipping COG conversion; already valid: s3://%s/%s", bucket, key)
            return {"optimized": False, "skipped": "already_cog"}

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as dst_tmp:
            dst_path = dst_tmp.name

        log.info("Converting to COG in place: s3://%s/%s", bucket, key)
        convert_to_cog(src_path, dst_path, resampling=resampling)
        s3_client.upload_file(dst_path, bucket, key)
        return {"optimized": True, "skipped": None}
    finally:
        for path in (src_path, dst_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    log.warning("Could not remove temp file %s", path)
