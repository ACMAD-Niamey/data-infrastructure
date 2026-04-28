from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Station(models.Model):
    class StationType(models.TextChoices):
        SYNOP = "synop", "SYNOP"
        AWS = "aws", "Automatic Weather Station"
        AGRO = "agro", "Agrometeorological Station"
        RAINFALL = "rainfall", "Rainfall Station"
        CLIMATOLOGICAL = "climatological", "Climatological Station"
        HYDRO = "hydro", "Hydrological Station"
        OTHER = "other", "Other"

    station_code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Internal unique station code used by the platform.",
    )
    wmo_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="Official WMO station identifier where available.",
    )
    name = models.CharField(max_length=255)
    country_code = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_index=True,
        help_text="ISO 3166-1 alpha-3 country code.",
    )
    admin1 = models.CharField(max_length=150, blank=True, null=True)
    admin2 = models.CharField(max_length=150, blank=True, null=True)

    geom = models.PointField(
        geography=True,
        srid=4326,
        help_text="Station location stored as longitude/latitude point in WGS84.",
    )

    elevation_m = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Elevation in meters above sea level.",
    )
    agency = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Owning or operating agency.",
    )
    station_type = models.CharField(
        max_length=30,
        choices=StationType.choices,
        default=StationType.AWS,
        db_index=True,
    )
    install_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stations"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["station_code"], name="stations_code_idx"),
            models.Index(fields=["wmo_id"], name="stations_wmo_idx"),
            models.Index(fields=["country_code"], name="stations_country_idx"),
            models.Index(fields=["station_type"], name="stations_type_idx"),
            models.Index(fields=["is_active"], name="stations_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.station_code})"

    @property
    def longitude(self):
        return self.geom.x if self.geom else None

    @property
    def latitude(self):
        return self.geom.y if self.geom else None


class StationAlias(models.Model):
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    source_name = models.CharField(
        max_length=100,
        help_text="Source system name, e.g. WIS2, NOAA, OGIMET.",
    )
    alias_code = models.CharField(
        max_length=100,
        help_text="External source station code.",
    )
    alias_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional station name used by the external source.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "station_aliases"
        unique_together = ("source_name", "alias_code")
        indexes = [
            models.Index(fields=["source_name"], name="st_alias_source_idx"),
            models.Index(fields=["alias_code"], name="st_alias_code_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source_name}: {self.alias_code}"


class StationSensor(models.Model):
    class VariableCode(models.TextChoices):
        TEMPERATURE = "temp", "Air Temperature"
        RAINFALL = "rainfall", "Rainfall"
        HUMIDITY = "rh", "Relative Humidity"
        PRESSURE = "pressure", "Pressure"
        WIND_SPEED = "wind_speed", "Wind Speed"
        WIND_DIRECTION = "wind_direction", "Wind Direction"
        SOLAR_RADIATION = "solar_radiation", "Solar Radiation"
        SOIL_MOISTURE = "soil_moisture", "Soil Moisture"
        SOIL_TEMP = "soil_temp", "Soil Temperature"
        WATER_LEVEL = "water_level", "Water Level"
        OTHER = "other", "Other"

    class SensorStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        FAULTY = "faulty", "Faulty"
        MAINTENANCE = "maintenance", "Maintenance"

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="sensors",
    )
    sensor_code = models.CharField(
        max_length=100,
        help_text="Unique code for the sensor within the station.",
    )
    variable_code = models.CharField(
        max_length=50,
        choices=VariableCode.choices,
        db_index=True,
    )
    unit = models.CharField(
        max_length=50,
        help_text="Measurement unit, e.g. degC, mm, %, hPa.",
    )
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    install_date = models.DateField(blank=True, null=True)
    height_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(-10), MaxValueValidator(100)],
        help_text="Sensor height above ground in meters where applicable.",
    )
    status = models.CharField(
        max_length=20,
        choices=SensorStatus.choices,
        default=SensorStatus.ACTIVE,
        db_index=True,
    )
    metadata_json = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "station_sensors"
        unique_together = ("station", "sensor_code")
        indexes = [
            models.Index(fields=["station"], name="st_sensor_station_idx"),
            models.Index(fields=["variable_code"], name="st_sensor_var_idx"),
            models.Index(fields=["status"], name="st_sensor_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.station.station_code} - {self.variable_code} ({self.sensor_code})"