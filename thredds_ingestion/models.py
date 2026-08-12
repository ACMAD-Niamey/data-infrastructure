from django.db import models


class DownloadWorkflow(models.Model):
    """One THREDDS source: shared base URL, dated-folder pattern, and schedule."""

    name = models.CharField(
        max_length=150,
        unique=True,
        help_text="Admin label, e.g. 'ACMAD WWFD ensemble5'.",
    )
    source_base_url = models.URLField(
        max_length=500,
        help_text=(
            "THREDDS fileServer base (not the catalog/ HTML browsing base), e.g. "
            "https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5"
        ),
    )
    folder_pattern = models.CharField(
        max_length=200,
        default="{run_date:%Y%m%d}",
        help_text="Dated subfolder, rendered with run_date, e.g. {run_date:%Y%m%d}",
    )
    enabled = models.BooleanField(default=True)

    schedule_hour_utc = models.PositiveSmallIntegerField(
        default=7,
        help_text="Earliest UTC hour to attempt today's run.",
    )
    schedule_minute_utc = models.PositiveSmallIntegerField(default=0)
    retry_interval_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minutes between retries while any mapped file is not yet available.",
    )
    retry_until_hour_utc = models.PositiveSmallIntegerField(
        default=20,
        help_text="Stop retrying for the day after this UTC hour; the run is left partial.",
    )
    request_timeout_seconds = models.PositiveIntegerField(default=30)
    catch_up_days = models.PositiveSmallIntegerField(
        default=3,
        help_text=(
            "On every scheduled tick, also re-check this many previous days (not just "
            "today) and retry any that aren't completed yet - self-heals after an outage "
            "or a day with not-yet-available files, without operator intervention. "
            "For a large historical backfill, use the run_download_workflow management "
            "command instead of raising this."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DownloadWorkflowFile(models.Model):
    """One dataset + filename pattern mapped into a workflow."""

    workflow = models.ForeignKey(
        DownloadWorkflow,
        on_delete=models.CASCADE,
        related_name="files",
    )
    dataset = models.ForeignKey(
        "catalog.DatasetPage",
        on_delete=models.PROTECT,
        related_name="thredds_download_files",
        help_text="Target dataset (existing DatasetPage, matched by dataset_id).",
    )
    label = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Optional admin-facing label, e.g. '5-day mean' or 'POP 50mm'.",
    )
    filename_pattern = models.CharField(
        max_length=300,
        help_text=(
            "Rendered against run_date[, lead_hours, valid_date, threshold]. valid_date "
            "is run_date + lead_hours hours (as a date), and defaults to run_date when lead_hours is unset. "
            "Examples: "
            "'5daymean_{run_date:%Y%m%d}.tif', "
            "'mix{run_date:%Y%m%d}_{lead_hours}.tif', "
            "'pop{run_date:%Y%m%d}_{threshold}_{lead_hours}.tif', "
            "'heat_index_{run_date:%Y%m%d}_{valid_date:%Y%m%d}.tif' (lead_hours_csv in "
            "multiples of 24 for a day-granularity product like this one)."
        ),
    )
    lead_hours_csv = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text=(
            "Comma-separated lead hours, e.g. '24,96,144'. '0' is a valid lead (e.g. a "
            "same-day forecast in a '0,24,48' series) - leave the whole field blank "
            "instead for single-file-per-day products with no lead dimension at all."
        ),
    )
    threshold_label = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Literal substituted for {threshold} in filename_pattern, e.g. '50mm'.",
    )
    item_id_pattern = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text=(
            "Optional STAC item_id override, rendered with the same context as "
            "filename_pattern. Defaults to '{dataset_id}_{run_date:%Y%m%d}' (no lead "
            "hours) or '{dataset_id}_{run_date:%Y%m%d}_{lead_hours}h' (with lead hours). "
            "Must vary by lead_hours if this mapping has more than one - the default already does."
        ),
    )
    overwrite_existing = models.BooleanField(
        default=False,
        help_text="If true, re-download/re-ingest even when a DownloadRunItem already succeeded.",
    )
    csv_value_column = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=(
            "Required when the downloaded file is a CSV: name of the column holding "
            "raster values (e.g. 'Vigilance'). Converted to a GeoTIFF via "
            "utils.raster_converstions.csv_to_raster before upload/ingest - x/y "
            "columns and resolution use that function's defaults ('Data$x', 'y', 0.5°)."
        ),
    )
    datetime_from_run_date = models.BooleanField(
        default=False,
        help_text=(
            "If true, this item's STAC datetime (and valid_datetime) is run_date alone, "
            "ignoring lead_hours - use when the forecast issue date should be what's "
            "queryable/displayed (e.g. 'today's heat index outlook'), not the date the "
            "forecast is valid for. filename_pattern/item_id_pattern are unaffected - "
            "{valid_date}/{lead_hours} there still reflect the real lead. Also controls "
            "the start of the window below when validity_hours is set."
        ),
    )
    validity_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "If set, this item covers a window rather than an instant - it's ingested "
            "with start_datetime/end_datetime instead of a single datetime, e.g. 120 for "
            "a 5-day mean. The window starts at the same anchor datetime_from_run_date "
            "controls (run_date, or run_date + lead_hours) and ends validity_hours later. "
            "Leave blank for point-in-time products (the common case)."
        ),
    )
    enabled = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.label or self.filename_pattern

    def lead_hours_list(self) -> list[int]:
        raw = (self.lead_hours_csv or "").strip()
        if not raw:
            return []
        return [int(x.strip()) for x in raw.split(",") if x.strip()]


class DownloadRun(models.Model):
    """One execution of a workflow for one run_date, covering all its file mappings."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    workflow = models.ForeignKey(DownloadWorkflow, on_delete=models.CASCADE, related_name="runs")
    run_date = models.DateField(help_text="Forecast issue date rendered into folder_pattern/filename_pattern.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_attempted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Used to throttle retries via workflow.retry_interval_minutes.",
    )
    attempt_count = models.PositiveIntegerField(default=0)

    total_files = models.PositiveIntegerField(default=0)
    completed_files = models.PositiveIntegerField(default=0)
    failed_files = models.PositiveIntegerField(default=0)
    not_yet_available_files = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workflow", "run_date"], name="uniq_download_run_per_day"),
        ]
        indexes = [models.Index(fields=["workflow", "status"])]
        ordering = ["-run_date"]

    def __str__(self) -> str:
        return f"{self.workflow.name} {self.run_date:%Y-%m-%d} ({self.status})"


class DownloadRunItem(models.Model):
    """One resolved file within a run: one (workflow_file, lead_hours) pair."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        NOT_YET_AVAILABLE = "not_yet_available", "Not Yet Available"
        DOWNLOADING = "downloading", "Downloading"
        INGESTING = "ingesting", "Ingesting"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    run = models.ForeignKey(DownloadRun, on_delete=models.CASCADE, related_name="items")
    workflow_file = models.ForeignKey(
        DownloadWorkflowFile,
        on_delete=models.PROTECT,
        related_name="run_items",
    )
    # 0 is a sentinel for "no lead hour" (single-file-per-day products), never a real
    # lead hour. A nullable IntegerField would NOT enforce the uniqueness below on
    # Postgres, since NULL != NULL in a unique constraint.
    lead_hours = models.PositiveIntegerField(
        default=0,
        help_text="0 means this workflow_file has no lead-hour dimension.",
    )
    filename = models.CharField(max_length=300)
    source_url = models.URLField(max_length=600)
    item_id = models.CharField(
        max_length=250,
        unique=True,
        help_text=(
            "Deterministic STAC item id. Globally unique - a collision here almost "
            "always means item_id_pattern is missing {run_date} or {lead_hours}."
        ),
    )
    valid_datetime = models.DateTimeField(
        help_text=(
            "Window start (or the single instant, when workflow_file.validity_hours is "
            "unset): run_date + lead_hours, or run_date alone if datetime_from_run_date."
        ),
    )
    valid_end_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Window end (valid_datetime + workflow_file.validity_hours); blank for point-in-time items.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    ingestion_run_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ingest.models.IngestionRun.id this item was pushed through.",
    )
    minio_href = models.CharField(max_length=500, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "workflow_file", "lead_hours"],
                name="uniq_download_run_item_per_file_leadhour",
            ),
        ]
        indexes = [models.Index(fields=["status"])]
        ordering = ["workflow_file__sort_order", "lead_hours"]

    def __str__(self) -> str:
        return f"{self.item_id} ({self.status})"
