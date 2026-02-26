from minio import Minio
from tempfile import NamedTemporaryFile
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER") or os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD")
MINIO_ENDPOINT_PUBLIC = os.getenv("MINIO_ENDPOINT_PUBLIC", "minio.acmad.org:9000")

client = Minio(
    MINIO_ENDPOINT_PUBLIC,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

bucket = "geodata"
key = sys.argv[1]  #"path/your_big.tif"  
dest_key = key.replace(".tif", "_optimized.tif")

with NamedTemporaryFile(suffix=".tif") as src_tmp, NamedTemporaryFile(suffix=".tif") as dst_tmp:
    # Download original
    client.fget_object(bucket, key, src_tmp.name)

    profile = cog_profiles.get("deflate")

    config = dict(
        GDAL_NUM_THREADS="ALL_CPUS",
        RESAMPLING="average",        # or "nearest" if categorical
        OVERVIEWS="AUTO",
        OVERVIEW_RESAMPLING="average",
        BIGTIFF="IF_SAFER",
    )

    # Create optimized COG
    cog_translate(
        src_tmp.name,
        dst_tmp.name,
        profile,
        config=config,
        in_memory=False,
        quiet=False,
    )

    # Upload to SAME key (overwrites)
    client.fput_object(bucket, dest_key, dst_tmp.name)

print("File replaced with optimized COG.")