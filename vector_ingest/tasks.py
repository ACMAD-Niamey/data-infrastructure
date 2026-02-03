import os
import subprocess
from celery import shared_task
from django.conf import settings
from django.db import connections
from minio import Minio

from .models import VectorIngestJob

GIS_ALIAS = "gis"

def _gis_db():
    db = settings.DATABASES[GIS_ALIAS]
    return {
        "host": db["HOST"],
        "port": str(db.get("PORT", 5432)),
        "dbname": db["NAME"],
        "user": db["USER"],
        "password": db["PASSWORD"],
    }

def _minio_client():
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=getattr(settings, "MINIO_USE_SSL", False),
    )

@shared_task(bind=True)
def run_vector_ingest_pipeline(self, job_id: str):
    # Run in parallel: ingest unlocks tiles; archive is best-effort.
    ingest_to_postgis.delay(job_id)
    archive_to_minio.delay(job_id)

@shared_task(bind=True)
def ingest_to_postgis(self, job_id: str):
    job = VectorIngestJob.objects.get(id=job_id)
    job.ingest_status = "processing"
    job.ingest_error = ""
    job.save(update_fields=["ingest_status", "ingest_error", "updated_at"])

    schema = job.schema_name
    table = job.table_name
    srid = int(job.srid or 4326)
    path = job.upload.path

    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Upload not found: {path}")

        # Always operate on GIS db
        with connections[GIS_ALIAS].cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE;')

        db = _gis_db()
        env = os.environ.copy()
        env["PGPASSWORD"] = db["password"]

        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            f"PG:host={db['host']} port={db['port']} dbname={db['dbname']} user={db['user']}",
            path,
            "-nln", f"{schema}.{table}",
            "-lco", "GEOMETRY_NAME=geom",
            "-lco", "FID=id",
            "-nlt", "PROMOTE_TO_MULTI",
            "-t_srs", f"EPSG:{srid}",
            "-overwrite",
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"ogr2ogr failed:\n{proc.stderr}\n{proc.stdout}")

        with connections[GIS_ALIAS].cursor() as cur:
            cur.execute(
                f'CREATE INDEX IF NOT EXISTS "{table}_geom_gist" '
                f'ON "{schema}"."{table}" USING GIST (geom);'
            )
            cur.execute(f'ANALYZE "{schema}"."{table}";')
            cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}";')
            job.row_count = cur.fetchone()[0]

        job.ingest_status = "ready"
        job.save(update_fields=["ingest_status", "row_count", "updated_at"])

    except Exception as e:
        job.ingest_status = "failed"
        job.ingest_error = str(e)
        job.save(update_fields=["ingest_status", "ingest_error", "updated_at"])
        raise

@shared_task(bind=True)
def archive_to_minio(self, job_id: str):
    job = VectorIngestJob.objects.get(id=job_id)
    job.archive_status = "processing"
    job.archive_error = ""
    job.save(update_fields=["archive_status", "archive_error", "updated_at"])

    try:
        path = job.upload.path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Upload not found: {path}")

        bucket = getattr(settings, "MINIO_ARCHIVE_BUCKET", "geodata-archive")
        key = f"vector_ingest/{job.id}/{os.path.basename(path)}"

        client = _minio_client()
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        client.fput_object(bucket, key, path)
        job.archive_uri = f"s3://{bucket}/{key}"
        job.archive_status = "ready"
        job.save(update_fields=["archive_status", "archive_uri", "updated_at"])

    except Exception as e:
        # Best-effort: don't break ingestion
        job.archive_status = "failed"
        job.archive_error = str(e)
        job.save(update_fields=["archive_status", "archive_error", "updated_at"])
