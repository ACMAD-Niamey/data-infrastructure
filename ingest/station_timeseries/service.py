"""Orchestrates loading one logger CSV into stations + observations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from stations.models import Station
from weather_station_ingestion.services.observation_writer import (
    ObservationRow,
    ObservationWriter,
)

from .config import NIAMEY_BBOX, VARIABLES
from .filename import SensorIdentity, folder_context, parse_sensor_filename
from .geocoder import Geocoder, NominatimGeocoder
from .parser import GpsFix, MeasurementRow, parse_sensor_csv
from .registry import StationRegistry, ensure_dataset

logger = logging.getLogger(__name__)

WRITE_CHUNK = 5000


@dataclass
class IngestSummary:
    station_code: str
    observations_written: int
    rows_before_deployment: int
    rows_skipped: int
    deployed_from: datetime


class NoDeploymentFixError(ValueError):
    """The file has no GPS fix inside the study area, so we cannot place it."""


def in_study_area(fix: GpsFix, bbox: tuple[float, float, float, float] = NIAMEY_BBOX) -> bool:
    min_lat, min_lon, max_lat, max_lon = bbox
    return min_lat <= fix.lat <= max_lat and min_lon <= fix.lon <= max_lon


class StationTimeseriesIngestService:
    def __init__(
        self,
        *,
        geocoder: Geocoder | None = None,
        writer: ObservationWriter | None = None,
    ) -> None:
        self.registry = StationRegistry(geocoder or NominatimGeocoder())
        self.writer = writer or ObservationWriter()

    def ingest_file(
        self,
        path: str | Path,
        *,
        dataset_id: str,
        dataset_title: str,
        identity: SensorIdentity | None = None,
        context: dict[str, str] | None = None,
        payload_ref: str | None = None,
    ) -> IngestSummary:
        path = Path(path)
        identity = identity or parse_sensor_filename(path)
        context = context if context is not None else folder_context(path)

        parsed = parse_sensor_csv(path)
        fixes = [f for f in parsed.gps_fixes if in_study_area(f)]
        if not fixes:
            raise NoDeploymentFixError(
                f"{path.name}: no GPS fix inside the study area {NIAMEY_BBOX}"
            )

        # Everything logged before the first in-area fix is bench / transit data.
        deployed_from = min(f.observed_at for f in fixes)
        rows = [m for m in parsed.measurements if m.observed_at >= deployed_from]

        source, dataset = ensure_dataset(dataset_id, dataset_title)
        station = self.registry.upsert_station(
            identity=identity, fixes=fixes, dataset_id=dataset_id, context=context
        )
        sensors = self.registry.ensure_sensors(station)

        written = self._write(
            rows, station=station, sensors=sensors,
            dataset_id=dataset.id, source_id=source.id,
            payload_ref=payload_ref or path.name,
        )
        Station.objects.filter(pk=station.pk).update(has_observations=True)

        return IngestSummary(
            station_code=station.station_code,
            observations_written=written,
            rows_before_deployment=len(parsed.measurements) - len(rows),
            rows_skipped=parsed.skipped_rows,
            deployed_from=deployed_from,
        )

    def _write(self, rows, *, station, sensors, dataset_id, source_id, payload_ref) -> int:
        total = 0
        for chunk in _chunks(
            self._observation_rows(rows, station, sensors, dataset_id, source_id, payload_ref),
            WRITE_CHUNK,
        ):
            total += self.writer.insert_many(chunk)
        return total

    @staticmethod
    def _observation_rows(
        rows: list[MeasurementRow], station, sensors, dataset_id, source_id, payload_ref
    ) -> Iterator[ObservationRow]:
        for row in rows:
            for spec in VARIABLES:
                value = row.values.get(spec.column)
                if value is None:
                    continue
                yield ObservationRow(
                    station_id=station.id,
                    sensor_id=sensors[spec.column].id,
                    dataset_id=dataset_id,
                    source_id=source_id,
                    observed_at=row.observed_at.isoformat(),
                    variable_code=spec.variable_code,
                    raw_value=value,
                    # Cleaning is deferred: keep the value as logged and leave
                    # cleaned_value empty rather than inventing QC rules.
                    cleaned_value=None,
                    unit=spec.unit,
                    qc_flag="unchecked",
                    qc_notes=None,
                    payload_ref=payload_ref,
                )


def _chunks(items: Iterator[ObservationRow], size: int) -> Iterator[list[ObservationRow]]:
    chunk: list[ObservationRow] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
