from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db import connection


@dataclass
class ObservationRow:
    station_id: int
    sensor_id: int | None
    dataset_id: int
    source_id: int
    observed_at: str
    variable_code: str
    raw_value: float | None
    cleaned_value: float | None
    unit: str | None
    qc_flag: str
    qc_notes: str | None
    payload_ref: str | None


class ObservationWriter:
    insert_sql = """
        INSERT INTO observations (
            station_id,
            sensor_id,
            dataset_id,
            source_id,
            observed_at,
            variable_code,
            raw_value,
            cleaned_value,
            unit,
            qc_flag,
            qc_notes,
            ingest_time,
            payload_ref
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s
        )
        ON CONFLICT (station_id, variable_code, observed_at)
        DO UPDATE SET
            sensor_id = EXCLUDED.sensor_id,
            dataset_id = EXCLUDED.dataset_id,
            source_id = EXCLUDED.source_id,
            raw_value = EXCLUDED.raw_value,
            cleaned_value = EXCLUDED.cleaned_value,
            unit = EXCLUDED.unit,
            qc_flag = EXCLUDED.qc_flag,
            qc_notes = EXCLUDED.qc_notes,
            payload_ref = EXCLUDED.payload_ref;
    """

    def insert_many(self, rows: Iterable[ObservationRow]) -> int:
        rows = list(rows)
        if not rows:
            return 0

        params = [
            (
                row.station_id,
                row.sensor_id,
                row.dataset_id,
                row.source_id,
                row.observed_at,
                row.variable_code,
                row.raw_value,
                row.cleaned_value,
                row.unit,
                row.qc_flag,
                row.qc_notes,
                row.payload_ref,
            )
            for row in rows
        ]

        with connection.cursor() as cursor:
            cursor.executemany(self.insert_sql, params)

        return len(rows)