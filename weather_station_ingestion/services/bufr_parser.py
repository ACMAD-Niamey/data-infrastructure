from __future__ import annotations

import logging
import tempfile
import os
from dataclasses import dataclass

from weather_station_ingestion.services.observation_writer import ObservationRow, ObservationWriter
from weather_station_ingestion.services.station_enricher import StationEnricherService
from weather_station_ingestion.services.text_payload_parser import ExtractedStationObservation
from weather_station_ingestion.services.africa_filter import AfricaFilterService
from sources.models import DataSource, Dataset

log = logging.getLogger(__name__)


@dataclass
class BUFRNormalizationResult:
    parsed_count: int
    written_count: int
    skipped_count: int
    created_station_count: int
    created_sensor_count: int
    reason: str | None = None


# Mapping from BUFR descriptors to our internal variable codes
BUFR_VARIABLE_MAP = {
    "airTemperature": ("temp", "degC"),
    "airTemperatureAt2M": ("temp", "degC"),
    "dewpointTemperature": ("dewpoint", "degC"),
    "dewpointTemperatureAt2M": ("dewpoint", "degC"),
    "relativeHumidity": ("rh", "%"),
    "windSpeed": ("wind_speed", "m/s"),
    "windDirection": ("wind_direction", "deg"),
    "pressure": ("pressure", "Pa"),
    "pressureReducedToMeanSeaLevel": ("pressure", "hPa"),
    "nonCoordinatePressure": ("pressure", "Pa"),
    "totalPrecipitationOrTotalWaterEquivalent": ("rainfall", "kg m-2"),
    "totalPrecipitationPast1Hour": ("rainfall", "mm"),
    "totalPrecipitationPast3Hours": ("rainfall", "mm"),
    "totalPrecipitationPast6Hours": ("rainfall", "mm"),
    "totalPrecipitationPast12Hours": ("rainfall", "mm"),
    "totalPrecipitationPast24Hours": ("rainfall", "mm"),
    "horizontalVisibility": ("visibility", "m"),
    "heightOfStationGroundAboveMeanSeaLevel": ("elevation", "m"),
    "globalSolarRadiation": ("solar_radiation", "J m-2"),
}


def _kelvin_to_celsius(val: float | None) -> float | None:
    if val is None:
        return None
    # eccodes returns temperatures in Kelvin
    if val > 100:
        return round(val - 273.15, 2)
    return val


class BUFRParserService:
    def __init__(self) -> None:
        self.africa_filter = AfricaFilterService()
        self.writer = ObservationWriter()
        self.station_enricher = StationEnricherService()

    def _extract_observations(self, file_path: str) -> list[ExtractedStationObservation]:
        try:
            import eccodes
        except ImportError:
            log.error("eccodes not installed — cannot parse BUFR files")
            return []

        observations: list[ExtractedStationObservation] = []

        with open(file_path, "rb") as f:
            while True:
                bufr = eccodes.codes_bufr_new_from_file(f)
                if bufr is None:
                    break

                try:
                    eccodes.codes_set(bufr, "unpack", 1)

                    # Extract station identifiers
                    wmo_block = self._safe_get_long(eccodes, bufr, "blockNumber")
                    wmo_station = self._safe_get_long(eccodes, bufr, "stationNumber")
                    wmo_id = None
                    if wmo_block is not None and wmo_station is not None:
                        wmo_id = f"{wmo_block:02d}{wmo_station:03d}"

                    # Fallback: use WIGOS local identifier as station_code when
                    # the classic block/station number is absent (WIGOS-only files).
                    wigos_issuer = self._safe_get_long(eccodes, bufr, "wigosIssuerOfIdentifier")
                    wigos_local = self._safe_get_string(eccodes, bufr, "wigosLocalIdentifierCharacter")
                    wigos_station_code: str | None = None
                    if wigos_issuer is not None and wigos_local:
                        wigos_station_code = f"WIGOS_{wigos_issuer}_{wigos_local}"

                    station_name = self._safe_get_string(eccodes, bufr, "stationOrSiteName")
                    lat = self._safe_get_double(eccodes, bufr, "latitude")
                    lon = self._safe_get_double(eccodes, bufr, "longitude")

                    # Skip invalid coordinates
                    if lat is not None and (lat < -90 or lat > 90):
                        lat = None
                    if lon is not None and (lon < -180 or lon > 180):
                        lon = None

                    # Extract datetime
                    year = self._safe_get_long(eccodes, bufr, "year")
                    month = self._safe_get_long(eccodes, bufr, "month")
                    day = self._safe_get_long(eccodes, bufr, "day")
                    hour = self._safe_get_long(eccodes, bufr, "hour")
                    minute = self._safe_get_long(eccodes, bufr, "minute")

                    if not all(v is not None for v in (year, month, day, hour)):
                        continue

                    observed_at = (
                        f"{year:04d}-{month:02d}-{day:02d}"
                        f"T{hour:02d}:{(minute or 0):02d}:00+00:00"
                    )

                    # Extract variables
                    for bufr_key, (var_code, unit) in BUFR_VARIABLE_MAP.items():
                        value = self._safe_get_double(eccodes, bufr, bufr_key)
                        if value is None:
                            continue

                        # Convert Kelvin to Celsius for temperature variables
                        if var_code in ("temp", "dewpoint"):
                            value = _kelvin_to_celsius(value)

                        observations.append(
                            ExtractedStationObservation(
                                source_name="bufr",
                                wmo_id=wmo_id,
                                station_code=wmo_id or wigos_station_code,
                                station_name=station_name,
                                latitude=lat,
                                longitude=lon,
                                country_code=None,
                                observed_at=observed_at,
                                variable_code=var_code,
                                value=value,
                                unit=unit,
                                sensor_code=f"{var_code.upper()}_BUFR",
                                qc_flag="unchecked",
                                qc_notes=f"bufr_key={bufr_key}",
                            )
                        )

                except Exception as exc:
                    log.warning("Failed to unpack BUFR message: %s", exc)
                finally:
                    eccodes.codes_release(bufr)

        return observations

    def _safe_get_long(self, eccodes, handle, key: str) -> int | None:
        try:
            val = eccodes.codes_get_long(handle, key)
            if val == eccodes.CODES_MISSING_LONG:
                return None
            return val
        except Exception:
            return None

    def _safe_get_double(self, eccodes, handle, key: str) -> float | None:
        try:
            val = eccodes.codes_get_double(handle, key)
            if val == eccodes.CODES_MISSING_DOUBLE or val > 1e30:
                return None
            return val
        except Exception:
            return None

    def _safe_get_string(self, eccodes, handle, key: str) -> str | None:
        try:
            val = eccodes.codes_get_string(handle, key)
            if not val or val == "MISSING":
                return None
            return val.strip()
        except Exception:
            return None

    def parse_and_write(
        self,
        *,
        file_path: str,
        dataset: Dataset,
        source: DataSource,
        payload_ref: str | None = None,
    ) -> BUFRNormalizationResult:
        candidates = self._extract_observations(file_path)

        rows: list[ObservationRow] = []
        skipped = 0
        created_station_count = 0
        created_sensor_count = 0

        for candidate in candidates:
            enrichment = self.station_enricher.resolve_or_create(
                obs=candidate,
                source_name=source.source_code,
            )

            if enrichment.station_action == "created":
                created_station_count += 1
            if enrichment.sensor_action == "created":
                created_sensor_count += 1

            if not enrichment.station:
                skipped += 1
                continue

            africa_result = self.africa_filter.from_station(enrichment.station)
            if not africa_result.is_candidate:
                skipped += 1
                continue

            if not candidate.observed_at or not candidate.variable_code:
                skipped += 1
                continue

            rows.append(
                ObservationRow(
                    station_id=enrichment.station.id,
                    sensor_id=enrichment.sensor.id if enrichment.sensor else None,
                    dataset_id=dataset.id,
                    source_id=source.id,
                    observed_at=candidate.observed_at,
                    variable_code=candidate.variable_code,
                    raw_value=candidate.value,
                    cleaned_value=candidate.value,
                    unit=candidate.unit,
                    qc_flag=candidate.qc_flag,
                    qc_notes=candidate.qc_notes,
                    payload_ref=payload_ref,
                )
            )

        written = self.writer.insert_many(rows)

        return BUFRNormalizationResult(
            parsed_count=len(candidates),
            written_count=written,
            skipped_count=skipped,
            created_station_count=created_station_count,
            created_sensor_count=created_sensor_count,
            reason=None if written else "no_matching_african_observations",
        )
