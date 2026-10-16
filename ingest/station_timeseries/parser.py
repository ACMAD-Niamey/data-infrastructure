"""Parse a heat-campaign logger CSV into GPS fixes and measurement rows."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import GPS_PHASE_PREFIX, MEASUREMENT_PHASE, VARIABLES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpsFix:
    observed_at: datetime
    lat: float
    lon: float
    alt_m: float | None


@dataclass(frozen=True)
class MeasurementRow:
    observed_at: datetime
    # column name -> value; None when the channel was empty on that minute.
    values: dict[str, float | None]


@dataclass
class ParsedSensorFile:
    gps_fixes: list[GpsFix] = field(default_factory=list)
    measurements: list[MeasurementRow] = field(default_factory=list)
    skipped_rows: int = 0


def _to_float(raw: str | None) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _to_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_sensor_csv(path: str | Path) -> ParsedSensorFile:
    """Read the whole file. Malformed rows are counted, never raised, so one bad
    line from a field logger cannot abort a 100k-row load."""
    parsed = ParsedSensorFile()
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            observed_at = _to_datetime(row.get("timestamp_utc"))
            if observed_at is None:
                parsed.skipped_rows += 1
                continue

            phase = (row.get("phase") or "").strip()
            if phase.startswith(GPS_PHASE_PREFIX):
                lat, lon = _to_float(row.get("lat")), _to_float(row.get("lon"))
                if lat is None or lon is None:
                    parsed.skipped_rows += 1
                    continue
                parsed.gps_fixes.append(
                    GpsFix(observed_at, lat, lon, _to_float(row.get("alt_m")))
                )
            elif phase == MEASUREMENT_PHASE:
                parsed.measurements.append(
                    MeasurementRow(
                        observed_at,
                        {spec.column: _to_float(row.get(spec.column)) for spec in VARIABLES},
                    )
                )
            else:
                parsed.skipped_rows += 1

    logger.info(
        "Parsed %s: %d gps fixes, %d measurements, %d skipped",
        path, len(parsed.gps_fixes), len(parsed.measurements), parsed.skipped_rows,
    )
    return parsed
