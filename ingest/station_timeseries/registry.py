"""Create / update the Station, StationSensor and source records for a sensor."""

from __future__ import annotations

from statistics import median

from django.contrib.gis.geos import Point

from sources.models import DataSource, Dataset, Policy
from stations.models import Station, StationSensor

from .config import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_COUNTRY_NAME,
    EXPOSURE_LABEL_EN,
    VARIABLES,
)
from .filename import SensorIdentity
from .geocoder import Geocoder
from .parser import GpsFix

DEFAULT_POLICY_NAME = "Station time series (public)"


def ensure_dataset(dataset_id: str, title: str) -> tuple[DataSource, Dataset]:
    """Observation rows must reference sources.Dataset / DataSource. They are
    keyed by the Wagtail DatasetPage.dataset_id so the CMS page and the
    observations stay linked without a foreign key between the two apps."""
    policy, _ = Policy.objects.get_or_create(
        name=DEFAULT_POLICY_NAME,
        defaults={"public_api_allowed": True, "dashboard_allowed": True},
    )
    source, _ = DataSource.objects.get_or_create(
        source_code=f"station_ts_{dataset_id}",
        defaults={
            "source_name": title,
            "source_type": DataSource.SourceType.OTHER,
            "protocol": DataSource.ProtocolType.FILE,
        },
    )
    dataset, _ = Dataset.objects.get_or_create(
        dataset_code=dataset_id,
        defaults={
            "source": source,
            "policy": policy,
            "dataset_name": title,
            "variable_family": "station_timeseries",
            "temporal_resolution": "1min",
        },
    )
    return source, dataset


def median_position(fixes: list[GpsFix]) -> tuple[float, float, float | None]:
    """Median, not mean: a handful of poor boot-time fixes would otherwise drag
    a fixed sensor tens of metres off its true spot."""
    alts = [f.alt_m for f in fixes if f.alt_m is not None]
    return (
        median(f.lat for f in fixes),
        median(f.lon for f in fixes),
        median(alts) if alts else None,
    )


class StationRegistry:
    def __init__(self, geocoder: Geocoder) -> None:
        self.geocoder = geocoder

    def upsert_station(
        self,
        *,
        identity: SensorIdentity,
        fixes: list[GpsFix],
        dataset_id: str,
        context: dict[str, str],
        country_code: str = DEFAULT_COUNTRY_CODE,
    ) -> Station:
        lat, lon, alt = median_position(fixes)
        existing = Station.objects.filter(station_code=identity.station_code).first()
        metadata = dict((existing.metadata_json or {}) if existing else {})

        # Geocode once per station: it is a network call with a 1 req/s limit
        # and the place of a fixed sensor does not change between reloads.
        site = metadata.get("site") or self.geocoder.place_name(lat, lon)
        metadata.update(
            {
                "dataset_code": dataset_id,
                "sensor_number": identity.sensor_number,
                "exposure": identity.exposure,
                "site": site,
                **{k: v for k, v in context.items() if v},
            }
        )

        label = EXPOSURE_LABEL_EN.get(identity.exposure or "", "")
        name = f"{site or 'Niamey'} - Sensor {identity.sensor_number}" + (
            f" ({label})" if label else ""
        )
        station, _ = Station.objects.update_or_create(
            station_code=identity.station_code,
            defaults={
                "name": name,
                "geom": Point(lon, lat, srid=4326),
                "elevation_m": round(alt, 2) if alt is not None else None,
                "country_code": country_code,
                "country_name": DEFAULT_COUNTRY_NAME,
                "station_type": Station.StationType.OTHER,
                "is_active": True,
                "metadata_json": metadata,
            },
        )
        return station

    @staticmethod
    def ensure_sensors(station: Station) -> dict[str, StationSensor]:
        """column name -> StationSensor."""
        sensors: dict[str, StationSensor] = {}
        for spec in VARIABLES:
            sensor, _ = StationSensor.objects.get_or_create(
                station=station,
                sensor_code=spec.column,
                defaults={"variable_code": spec.variable_code, "unit": spec.unit},
            )
            sensors[spec.column] = sensor
        return sensors
