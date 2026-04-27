from __future__ import annotations

from dataclasses import dataclass

from weather_station_ingestion.services.africa_filter import AfricaFilterService
from weather_station_ingestion.services.observation_writer import ObservationRow, ObservationWriter
from weather_station_ingestion.services.json_payload_parser import JSONPayloadParserFactory
from weather_station_ingestion.services.station_enricher import StationEnricherService
from sources.models import DataSource, Dataset


@dataclass
class JSONNormalizationResult:
    parsed_count: int
    written_count: int
    skipped_count: int
    created_station_count: int
    created_sensor_count: int
    reason: str | None = None


class JSONPayloadNormalizationService:
    def __init__(self) -> None:
        self.africa_filter = AfricaFilterService()
        self.writer = ObservationWriter()
        self.station_enricher = StationEnricherService()

    def normalize_and_write(
        self,
        *,
        payload: dict,
        dataset: Dataset,
        source: DataSource,
        payload_ref: str | None = None,
    ) -> JSONNormalizationResult:
        parser = JSONPayloadParserFactory.get_parser(payload)
        candidates = parser.parse(payload)

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

        return JSONNormalizationResult(
            parsed_count=len(candidates),
            written_count=written,
            skipped_count=skipped,
            created_station_count=created_station_count,
            created_sensor_count=created_sensor_count,
            reason=None if written else "no_matching_african_observations",
        )