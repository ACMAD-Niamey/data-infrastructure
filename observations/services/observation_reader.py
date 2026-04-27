from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import connection


@dataclass
class ObservationRecord:
    station_id: int
    sensor_id: int | None
    dataset_id: int
    source_id: int
    observed_at: Any
    variable_code: str
    raw_value: float | None
    cleaned_value: float | None
    unit: str | None
    qc_flag: str
    qc_notes: str | None
    ingest_time: Any
    payload_ref: str | None


class ObservationReader:
    base_select = """
        SELECT
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
        FROM observations
    """

    def _fetch(self, sql: str, params: list[Any] | None = None) -> list[ObservationRecord]:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])
            rows = cursor.fetchall()

        return [ObservationRecord(*row) for row in rows]

    def latest(self, limit: int = 10) -> list[ObservationRecord]:
        sql = f"""
            {self.base_select}
            ORDER BY observed_at DESC
            LIMIT %s
        """
        return self._fetch(sql, [limit])

    def by_station(self, station_id: int, limit: int = 100) -> list[ObservationRecord]:
        sql = f"""
            {self.base_select}
            WHERE station_id = %s
            ORDER BY observed_at DESC
            LIMIT %s
        """
        return self._fetch(sql, [station_id, limit])

    def by_variable(self, variable_code: str, limit: int = 100) -> list[ObservationRecord]:
        sql = f"""
            {self.base_select}
            WHERE variable_code = %s
            ORDER BY observed_at DESC
            LIMIT %s
        """
        return self._fetch(sql, [variable_code, limit])

    def latest_for_station_variable(
        self,
        station_id: int,
        variable_code: str,
        limit: int = 50,
    ) -> list[ObservationRecord]:
        sql = f"""
            {self.base_select}
            WHERE station_id = %s
              AND variable_code = %s
            ORDER BY observed_at DESC
            LIMIT %s
        """
        return self._fetch(sql, [station_id, variable_code, limit])
    
    def latest_with_station_metadata(self, limit: int = 10) -> list[dict]:
        sql = """
            SELECT
                o.station_id,
                s.station_code,
                s.name AS station_name,
                s.country_code,
                ST_Y(s.geom::geometry) AS latitude,
                ST_X(s.geom::geometry) AS longitude,
                o.sensor_id,
                o.dataset_id,
                o.source_id,
                o.observed_at,
                o.variable_code,
                o.raw_value,
                o.cleaned_value,
                o.unit,
                o.qc_flag,
                o.qc_notes,
                o.ingest_time,
                o.payload_ref
            FROM observations o
            JOIN stations s ON o.station_id = s.id
            ORDER BY o.observed_at DESC
            LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [limit])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]