from django.db import models


class Policy(models.Model):
    name = models.CharField(max_length=150, unique=True)
    owner_org = models.CharField(max_length=255, blank=True, null=True)

    public_api_allowed = models.BooleanField(default=False)
    dashboard_allowed = models.BooleanField(default=False)
    internal_allowed = models.BooleanField(default=True)
    partner_allowed = models.BooleanField(default=False)
    raw_download_allowed = models.BooleanField(default=False)
    aggregate_allowed = models.BooleanField(default=True)
    station_visible = models.BooleanField(default=True)

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "policies"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DataSource(models.Model):
    class SourceType(models.TextChoices):
        WIS2 = "wis2", "WIS2"
        NOAA = "noaa", "NOAA"
        OGIMET = "ogimet", "Ogimet"
        NATIONAL_MET = "national_met", "National Meteorological Service"
        AWS_DIRECT = "aws_direct", "Direct AWS Feed"
        OTHER = "other", "Other"

    class ProtocolType(models.TextChoices):
        MQTT = "mqtt", "MQTT"
        HTTP = "http", "HTTP"
        HTTPS = "https", "HTTPS"
        FTP = "ftp", "FTP"
        SFTP = "sftp", "SFTP"
        FILE = "file", "File"
        API = "api", "API"
        OTHER = "other", "Other"

    source_code = models.CharField(max_length=100, unique=True)
    source_name = models.CharField(max_length=255)
    source_type = models.CharField(
        max_length=50,
        choices=SourceType.choices,
        default=SourceType.OTHER,
        db_index=True,
    )
    endpoint_url = models.URLField(blank=True, null=True)
    protocol = models.CharField(
        max_length=20,
        choices=ProtocolType.choices,
        default=ProtocolType.OTHER,
    )
    contact_info = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_sources"
        ordering = ["source_name"]

    def __str__(self) -> str:
        return f"{self.source_name} ({self.source_code})"


class Dataset(models.Model):
    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="datasets",
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name="datasets",
    )

    dataset_code = models.CharField(max_length=120, unique=True)
    dataset_name = models.CharField(max_length=255)
    variable_family = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Example: synop, rainfall, temperature, station_health.",
    )
    temporal_resolution = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Example: 10min, hourly, daily.",
    )
    licence_text = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "datasets"
        ordering = ["dataset_name"]
        indexes = [
            models.Index(fields=["dataset_code"], name="datasets_code_idx"),
            models.Index(fields=["is_active"], name="datasets_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.dataset_name} ({self.dataset_code})"