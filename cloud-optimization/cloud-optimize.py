from minio import Minio
from minio.commonconfig import CopySource
from tempfile import NamedTemporaryFile
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import sys
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER") or os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD")
MINIO_ENDPOINT_PUBLIC = "minio.acmad.org" #os.getenv("MINIO_ENDPOINT_PUBLIC", "minio.acmad.org:9000")

client = Minio(
    MINIO_ENDPOINT_PUBLIC,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=True,
)

bucket = "geodata"
key = sys.argv[1]  #"path/your_big.tif"
dest_key = key.replace(".tif", "_optimized.tif")

with NamedTemporaryFile(suffix=".tif") as src_tmp, NamedTemporaryFile(suffix=".tif") as dst_tmp:
    # Download original
    client.fget_object(bucket, key, src_tmp.name)

    profile = cog_profiles.get("deflate")

    profile.update({
    "BIGTIFF": "YES",          # or "IF_SAFER"
    "blocksize": 512,
    "compress": "DEFLATE",
    "predictor": 2,
})

    config = dict(
        GDAL_NUM_THREADS="ALL_CPUS"
    )

    # Create optimized COG
    cog_translate(
        src_tmp.name,
        dst_tmp.name,
        profile,
        config=config,
        in_memory=False,
        quiet=False,
        overview_resampling="average",
         resampling="average",
    )

    # Upload to a staging key first, then server-side copy into the final
    # dest_key in one atomic call. TiTiler/GDAL's vsicurl caches a 404 the
    # moment anything requests dest_key while it's mid-upload, and that
    # negative cache entry sticks around for the life of the TiTiler
    # process — so dest_key must never be observable in a partial state.
    # Note: copy_object is a single-request server-side copy, capped at
    # 5GiB by the S3/MinIO API — fine for current COG sizes, but a source
    # file above that would need a multipart copy instead.
    staging_key = f"{dest_key}.staging-{uuid.uuid4().hex}"
    try:
        client.fput_object(bucket, staging_key, dst_tmp.name)
        client.copy_object(bucket, dest_key, CopySource(bucket, staging_key))
    finally:
        client.remove_object(bucket, staging_key)

log.info("File replaced with optimized COG.")
