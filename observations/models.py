from django.db import models


class Observation(models.Model):
    station = models.ForeignKey(
        "stations.Station",
        on_delete=models.DO_NOTHING,
        related_name="observations",
    )
    sensor = models.ForeignKey(
        "stations.StationSensor",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="observations",
    )
    dataset = models.ForeignKey(
        "sources.Dataset",
        on_delete=models.DO_NOTHING,
        related_name="observations",
    )
    source = models.ForeignKey(
        "sources.DataSource",
        on_delete=models.DO_NOTHING,
        related_name="observations",
    )

    observed_at = models.DateTimeField()
    variable_code = models.CharField(max_length=50)
    raw_value = models.FloatField(null=True, blank=True)
    cleaned_value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    qc_flag = models.CharField(max_length=20, default="unchecked")
    qc_notes = models.TextField(null=True, blank=True)
    ingest_time = models.DateTimeField()
    payload_ref = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "observations"

    def __str__(self):
        return f"{self.station_id} - {self.variable_code} @ {self.observed_at}"


class StationHealth(models.Model):
    class HealthStatus(models.TextChoices):
        OK = "ok", "OK"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"
        OFFLINE = "offline", "Offline"
        UNKNOWN = "unknown", "Unknown"

    station = models.ForeignKey(
        "stations.Station",
        on_delete=models.CASCADE,
        related_name="health_records",
    )
    observed_at = models.DateTimeField(db_index=True)

    battery_voltage = models.FloatField(blank=True, null=True)
    signal_strength = models.FloatField(blank=True, null=True)
    internal_temp = models.FloatField(blank=True, null=True)
    uptime_seconds = models.BigIntegerField(blank=True, null=True)
    packet_loss_pct = models.FloatField(blank=True, null=True)

    health_status = models.CharField(
        max_length=20,
        choices=HealthStatus.choices,
        default=HealthStatus.UNKNOWN,
        db_index=True,
    )
    ingest_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "station_health"
        indexes = [
            models.Index(fields=["station", "observed_at"], name="health_station_time_idx"),
            models.Index(fields=["health_status"], name="health_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.station.station_code} - {self.health_status} @ {self.observed_at}"