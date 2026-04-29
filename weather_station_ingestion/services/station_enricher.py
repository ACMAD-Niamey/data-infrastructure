from __future__ import annotations

from dataclasses import dataclass

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from stations.models import Station, StationAlias, StationSensor
from stations.services.station_geography_enricher import StationGeographyEnricher
from weather_station_ingestion.services.text_payload_parser import ExtractedStationObservation

# Maximum distance for coordinate-based station matching.
_COORD_MATCH_TOLERANCE_M = 5_000


@dataclass
class StationEnrichmentResult:
    station: Station | None
    sensor: StationSensor | None
    station_action: str
    sensor_action: str
    alias_action: str


class StationEnricherService:
    def __init__(self) -> None:
        self.geography_enricher = StationGeographyEnricher()

    def _match_station(self, obs: ExtractedStationObservation) -> Station | None:
        if obs.wmo_id:
            station = Station.objects.filter(wmo_id=obs.wmo_id).first()
            if station:
                return station

        if obs.station_code:
            station = Station.objects.filter(station_code=obs.station_code).first()
            if station:
                return station

            alias = (
                StationAlias.objects
                .select_related("station")
                .filter(alias_code=obs.station_code)
                .first()
            )
            if alias:
                return alias.station

        # Coordinate proximity fallback: useful for BUFR/WIGOS messages that
        # carry no classic WMO block/station number but do have valid lat/lon.
        if self._coords_valid(obs.latitude, obs.longitude):
            point = Point(obs.longitude, obs.latitude, srid=4326)
            station = (
                Station.objects
                .filter(geom__distance_lte=(point, D(m=_COORD_MATCH_TOLERANCE_M)))
                .order_by("geom")   # PostGIS picks nearest within tolerance
                .first()
            )
            if station:
                return station

        return None

    @staticmethod
    def _coords_valid(lat: float | None, lon: float | None) -> bool:
        if lat is None or lon is None:
            return False
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        if lat == 0.0 and lon == 0.0:
            return False
        return True

    def _can_create_station(self, obs: ExtractedStationObservation) -> bool:
        if not self._coords_valid(obs.latitude, obs.longitude):
            return False
        return bool(obs.wmo_id or obs.station_code)

    def _build_point(self, obs: ExtractedStationObservation):
        if not self._coords_valid(obs.latitude, obs.longitude):
            return None
        return Point(obs.longitude, obs.latitude)

    def _update_station_if_needed(self, station: Station, obs: ExtractedStationObservation) -> str:
        changed = False

        if not station.wmo_id and obs.wmo_id:
            station.wmo_id = obs.wmo_id
            changed = True

        if not station.name and obs.station_name:
            station.name = obs.station_name
            changed = True

        if not station.country_code and obs.country_code:
            station.country_code = obs.country_code.upper()
            changed = True

        if station.geom is None and obs.latitude is not None and obs.longitude is not None:
            station.geom = self._build_point(obs)
            changed = True

        if changed:
            station.save()
            self.geography_enricher.enrich_station_geography(station)
            return "updated"

        return "matched"

    def _create_station(self, obs: ExtractedStationObservation) -> Station | None:
        if not self._can_create_station(obs):
            return None

        station_code = obs.station_code or obs.wmo_id
        if not station_code:
            return None

        name = obs.station_name or station_code
        station = Station.objects.create(
            station_code=station_code,
            wmo_id=obs.wmo_id,
            name=name,
            country_code=(obs.country_code or "").upper() or None,
            geom=self._build_point(obs),
            station_type=Station.StationType.AWS,
            is_active=True,
        )
        self.geography_enricher.enrich_station_geography(station)
        return station

    def _ensure_alias(self, station: Station, source_name: str | None, alias_code: str | None, alias_name: str | None) -> str:
        if not source_name or not alias_code:
            return "none"

        alias, created = StationAlias.objects.get_or_create(
            source_name=source_name,
            alias_code=alias_code,
            defaults={
                "station": station,
                "alias_name": alias_name,
            },
        )
        if created:
            return "created"

        if alias.station_id != station.id:
            alias.station = station
            alias.save(update_fields=["station"])
            return "updated"

        return "matched"

    def _ensure_sensor(self, station: Station, obs: ExtractedStationObservation) -> tuple[StationSensor | None, str]:
        if not obs.variable_code:
            return None, "none"

        sensor_code = obs.sensor_code or f"{obs.variable_code.upper()}_AUTO"

        sensor, created = StationSensor.objects.get_or_create(
            station=station,
            sensor_code=sensor_code,
            defaults={
                "variable_code": obs.variable_code,
                "unit": obs.unit or "",
                "status": StationSensor.SensorStatus.ACTIVE,
            },
        )
        if created:
            return sensor, "created"

        changed = False
        if not sensor.unit and obs.unit:
            sensor.unit = obs.unit
            changed = True
        if changed:
            sensor.save(update_fields=["unit"])
            return sensor, "updated"

        return sensor, "matched"

    def resolve_or_create(self, obs: ExtractedStationObservation, source_name: str | None) -> StationEnrichmentResult:
        station = self._match_station(obs)

        if station:
            station_action = self._update_station_if_needed(station, obs)
        else:
            station = self._create_station(obs)
            station_action = "created" if station else "skipped"

        if not station:
            return StationEnrichmentResult(
                station=None,
                sensor=None,
                station_action="skipped",
                sensor_action="none",
                alias_action="none",
            )

        if not station.canonical_code or not station.country_name or not station.admin1:
            self.geography_enricher.enrich_station_geography(station)

        alias_action = self._ensure_alias(
            station=station,
            source_name=source_name,
            alias_code=obs.station_code,
            alias_name=obs.station_name,
        )

        sensor, sensor_action = self._ensure_sensor(station, obs)

        return StationEnrichmentResult(
            station=station,
            sensor=sensor,
            station_action=station_action,
            sensor_action=sensor_action,
            alias_action=alias_action,
        )