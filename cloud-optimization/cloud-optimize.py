from minio import Minio
from tempfile import NamedTemporaryFile
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import sys
import os
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

    # Upload to SAME key (overwrites)
    client.fput_object(bucket, dest_key, dst_tmp.name)

log.info("File replaced with optimized COG.")