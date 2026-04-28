from django.db import models


class RawPayloadLog(models.Model):
    class SourceType(models.TextChoices):
        WIS2 = "wis2", "WIS2"
        NOAA = "noaa", "NOAA"
        OGIMET = "ogimet", "OGIMET"
        NATIONAL_MET = "national_met", "National Met"
        OTHER = "other", "Other"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        DOWNLOADED = "downloaded", "Downloaded"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    source_type = models.CharField(
        max_length=30,
        choices=SourceType.choices,
        default=SourceType.WIS2,
        db_index=True,
    )
    source_identifier = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
    )
    topic = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    data_id = models.CharField(max_length=500, blank=True, null=True, db_index=True)
    metadata_id = models.CharField(max_length=500, blank=True, null=True)
    canonical_url = models.TextField(blank=True, null=True)
    content_type = models.CharField(max_length=100, blank=True, null=True)
    pubtime = models.DateTimeField(blank=True, null=True, db_index=True)
    data_datetime = models.DateTimeField(blank=True, null=True, db_index=True)
    global_cache = models.CharField(max_length=255, blank=True, null=True)

    payload = models.JSONField(blank=True, null=True)

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
    decision = models.CharField(max_length=100, blank=True, null=True)
    payload_size_bytes = models.BigIntegerField(blank=True, null=True)
    downloaded_content_type = models.CharField(max_length=150, blank=True, null=True)
    payload_preview = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    local_file_path = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "raw_payload_logs"
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.source_type} | {self.processing_status} | {self.source_identifier}"


class IngestionJob(models.Model):
    class JobType(models.TextChoices):
        WIS2_CONSUMER = "wis2_consumer", "WIS2 Consumer"
        NOAA_IMPORT = "noaa_import", "NOAA Import"
        OGIMET_IMPORT = "ogimet_import", "OGIMET Import"
        MANUAL_UPLOAD = "manual_upload", "Manual Upload"
        OTHER = "other", "Other"

    class JobStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial Success"

    job_type = models.CharField(
        max_length=30,
        choices=JobType.choices,
        default=JobType.WIS2_CONSUMER,
        db_index=True,
    )
    job_status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    source_name = models.CharField(max_length=255, blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    records_received = models.PositiveIntegerField(default=0)
    records_processed = models.PositiveIntegerField(default=0)
    records_failed = models.PositiveIntegerField(default=0)
    details = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ingestion_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job_type} | {self.job_status} | {self.created_at}"