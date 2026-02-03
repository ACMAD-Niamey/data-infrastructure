import uuid
from django.db import models

class VectorIngestJob(models.Model):
    STATUS = (
        ("pending", "pending"),
        ("processing", "processing"),
        ("ready", "ready"),
        ("failed", "failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    dataset_name = models.CharField(max_length=255)
    table_name = models.CharField(max_length=63)          # target table
    schema_name = models.CharField(max_length=63, default="public")  # TiPG MVP
    srid = models.IntegerField(default=4326)

    upload = models.FileField(upload_to="vector_uploads/%Y/%m/%d/")

    ingest_status = models.CharField(max_length=16, choices=STATUS, default="pending")
    ingest_error = models.TextField(blank=True, default="")

    archive_status = models.CharField(max_length=16, choices=STATUS, default="pending")
    archive_error = models.TextField(blank=True, default="")
    archive_uri = models.TextField(blank=True, default="")

    row_count = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
