from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from weather_station_ingestion.services.parser_registry import ParserRegistry
from weather_station_ingestion.services.text_payload_parser import ExtractedStationObservation

log = logging.getLogger(__name__)


class BaseJSONPayloadParser(ABC):
    format_name: str = "base_json"

    @abstractmethod
    def matches(self, payload: dict) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, payload: dict) -> list[ExtractedStationObservation]:
        raise NotImplementedError


@ParserRegistry.register_json_parser
class SimpleObservationJSONParser(BaseJSONPayloadParser):
    """
    Expected example:
    {
      "station": {
        "wmo_id": "63801",
        "station_code": "RWA_KGL_001",
        "station_name": "Kigali AWS",
        "latitude": -1.9441,
        "longitude": 30.0619,
        "country_code": "RWA"
      },
      "observations": [
        {
          "observed_at": "2026-03-14T10:00:00Z",
          "variable_code": "temp",
          "value": 24.5,
          "unit": "degC",
          "sensor_code": "TEMP_01"
        }
      ]
    }
    """

    def matches(self, payload: dict) -> bool:
        return "station" in payload and "observations" in payload

    def parse(self, payload: dict) -> list[ExtractedStationObservation]:
        station = payload.get("station", {}) or {}
        observations = payload.get("observations", []) or []

        rows: list[ExtractedStationObservation] = []
        for obs in observations:
            rows.append(
                ExtractedStationObservation(
                    source_name="json",
                    wmo_id=station.get("wmo_id"),
                    station_code=station.get("station_code"),
                    station_name=station.get("station_name"),
                    latitude=station.get("latitude"),
                    longitude=station.get("longitude"),
                    country_code=station.get("country_code"),
                    observed_at=obs.get("observed_at"),
                    variable_code=obs.get("variable_code"),
                    value=obs.get("value"),
                    unit=obs.get("unit"),
                    sensor_code=obs.get("sensor_code"),
                    qc_flag=obs.get("qc_flag", "unchecked"),
                    qc_notes=obs.get("qc_notes"),
                )
            )
        return rows


@ParserRegistry.register_json_parser
class WIS2FeatureCollectionParser(BaseJSONPayloadParser):
    """
    Handles WIS2 GeoJSON FeatureCollection payloads.
    Each Feature contains a geometry (Point) and properties with observation data.

    Expected structure:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [lon, lat]},
          "properties": {
            "wigos_station_identifier": "0-20000-0-63801",
            "wmo_station_id": "63801",
            "station_name": "Kigali",
            "country": "RWA",
            "resultTime": "2026-03-14T10:00:00Z",
            "name": "air_temperature",
            "value": 24.5,
            "units": "K"
          }
        }
      ]
    }
    """

    format_name = "wis2_feature_collection"

    # WIS2 property names can vary; map common ones
    _VARIABLE_MAP = {
        "air_temperature": ("temp", "degC", lambda v: round(v - 273.15, 2)),
        "dewpoint_temperature": ("dewpoint", "degC", lambda v: round(v - 273.15, 2)),
        "air_pressure": ("pressure_hpa", "hPa", lambda v: round(v / 100, 2) if v and v > 10000 else v),
        "wind_speed": ("wind_speed", "m/s", None),
        "wind_direction": ("wind_dir", "deg", None),
        "relative_humidity": ("humidity", "%", None),
        "precipitation_amount": ("rainfall", "mm", None),
    }

    def matches(self, payload: dict) -> bool:
        return (
            payload.get("type") == "FeatureCollection"
            and isinstance(payload.get("features"), list)
        )

    def parse(self, payload: dict) -> list[ExtractedStationObservation]:
        rows: list[ExtractedStationObservation] = []

        for feature in payload.get("features", []):
            if feature.get("type") != "Feature":
                continue

            props = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}

            lat, lon = self._extract_coords(geometry)
            wmo_id = props.get("wmo_station_id") or self._wmo_from_wigos(
                props.get("wigos_station_identifier")
            )
            station_name = props.get("station_name") or props.get("name", "")
            country_code = props.get("country") or props.get("country_code")
            observed_at = props.get("resultTime") or props.get("phenomenonTime")

            raw_name = props.get("name") or props.get("parameter_name", "")
            raw_value = props.get("value")
            raw_units = props.get("units") or props.get("unit", "")

            variable_code, unit, value = self._normalise_variable(raw_name, raw_value, raw_units)

            if variable_code and observed_at and value is not None:
                rows.append(
                    ExtractedStationObservation(
                        source_name="wis2_json",
                        wmo_id=str(wmo_id) if wmo_id else None,
                        station_code=props.get("wigos_station_identifier"),
                        station_name=station_name,
                        latitude=lat,
                        longitude=lon,
                        country_code=country_code,
                        observed_at=observed_at,
                        variable_code=variable_code,
                        value=value,
                        unit=unit,
                    )
                )

        return rows

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_coords(geometry: dict) -> tuple[float | None, float | None]:
        coords = geometry.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return coords[1], coords[0]  # GeoJSON is [lon, lat]
        return None, None

    @staticmethod
    def _wmo_from_wigos(wigos_id: str | None) -> str | None:
        """Extract traditional 5-digit WMO id from WIGOS identifier (0-20000-0-XXXXX)."""
        if not wigos_id:
            return None
        parts = wigos_id.split("-")
        return parts[-1] if len(parts) >= 4 else None

    def _normalise_variable(
        self, raw_name: str, raw_value, raw_units: str
    ) -> tuple[str | None, str | None, float | None]:
        """Map WIS2 variable name → our variable_code, converting units if needed."""
        mapping = self._VARIABLE_MAP.get(raw_name)
        if mapping:
            code, unit, converter = mapping
            try:
                val = float(raw_value) if raw_value is not None else None
            except (ValueError, TypeError):
                return None, None, None
            if converter and val is not None:
                val = converter(val)
            return code, unit, val

        # Unknown variable — pass through as-is
        if raw_value is not None:
            try:
                return raw_name, raw_units or None, float(raw_value)
            except (ValueError, TypeError):
                pass
        return None, None, None


class NullJSONPayloadParser(BaseJSONPayloadParser):
    format_name = "null_json"

    def matches(self, payload: dict) -> bool:
        return True

    def parse(self, payload: dict) -> list[ExtractedStationObservation]:
        return []


class JSONPayloadParserFactory:
    @classmethod
    def get_parser(cls, payload: dict) -> BaseJSONPayloadParser:
        for parser_cls in ParserRegistry.get_json_parsers():
            parser = parser_cls()
            if parser.matches(payload):
                return parser
        return NullJSONPayloadParser()