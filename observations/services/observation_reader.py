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
    
    # ------------------------------------------------------------------
    # Station-code-based queries (used by the stations stats API)
    # All aggregation is done in SQL — no ORM.
    # ------------------------------------------------------------------

    # Valid aggregation levels and their date_trunc unit
    _AGG_TRUNC = {
        "hourly": "hour",
        "daily": "day",
        "monthly": "month",
    }

    def station_info(self, station_code: str) -> dict | None:
        """Return basic metadata for a single station plus per-variable counts."""
        sql = """
            SELECT
                s.id,
                s.station_code,
                s.name,
                s.country_code,
                s.station_type,
                s.is_active,
                s.elevation_m,
                ST_Y(s.geom::geometry) AS latitude,
                ST_X(s.geom::geometry) AS longitude,
                COUNT(o.variable_code)  AS total_records,
                MIN(o.observed_at)      AS first_observation,
                MAX(o.observed_at)      AS last_observation
            FROM stations s
            LEFT JOIN observations o ON o.station_id = s.id
            WHERE s.station_code = %s
            GROUP BY s.id, s.station_code, s.name, s.country_code,
                     s.station_type, s.is_active, s.elevation_m,
                     s.geom
        """
        with connection.cursor() as cur:
            cur.execute(sql, [station_code])
            row = cur.fetchone()
            if row is None:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))

    def station_variables(self, station_code: str) -> list[dict]:
        """Return per-variable record counts + date ranges for a station."""
        sql = """
            SELECT
                o.variable_code,
                o.unit,
                COUNT(*)         AS record_count,
                MIN(o.observed_at) AS first_observation,
                MAX(o.observed_at) AS last_observation
            FROM observations o
            JOIN stations s ON s.id = o.station_id
            WHERE s.station_code = %s
            GROUP BY o.variable_code, o.unit
            ORDER BY o.variable_code
        """
        with connection.cursor() as cur:
            cur.execute(sql, [station_code])
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def station_list(self) -> list[dict]:
        """
        Return all active stations that have at least one observation,
        with the list of variables available and the most recent observation time.
        """
        sql = """
            SELECT
                s.id,
                s.station_code,
                s.name,
                s.country_code,
                s.station_type,
                s.elevation_m,
                ST_Y(s.geom::geometry) AS latitude,
                ST_X(s.geom::geometry) AS longitude,
                ARRAY_AGG(DISTINCT o.variable_code ORDER BY o.variable_code) AS variables_available,
                MAX(o.observed_at) AS latest_observed_at
            FROM stations s
            JOIN observations o ON o.station_id = s.id
            WHERE s.is_active = TRUE
              AND s.geom IS NOT NULL
            GROUP BY s.id, s.station_code, s.name, s.country_code,
                     s.station_type, s.elevation_m, s.geom
            ORDER BY s.country_code, s.name
        """
        with connection.cursor() as cur:
            cur.execute(sql)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def time_series_by_station_code(
        self,
        station_code: str,
        variable_code: str,
        start: str,
        end: str,
        agg: str = "daily",
    ) -> list[dict]:
        """
        Return aggregated (or raw) time-series for one variable at one station.

        Parameters
        ----------
        station_code : str   e.g. "60390"
        variable_code : str  e.g. "temp"
        start : str          ISO date/datetime, inclusive  e.g. "2026-04-01"
        end : str            ISO date/datetime, inclusive  e.g. "2026-04-27"
        agg : str            "raw" | "hourly" | "daily" | "monthly"

        Returns
        -------
        list of dicts with keys:
            period        – bucket start (or observed_at for raw)
            avg / min / max / count  – for aggregated modes
            value / unit             – for raw mode
        """
        if agg == "raw":
            sql = """
                SELECT
                    o.observed_at                                             AS period,
                    CASE
                        WHEN o.unit = 'Pa' THEN ROUND((o.raw_value / 100)::numeric, 2)
                        ELSE ROUND(o.raw_value::numeric, 4)
                    END                                                       AS value,
                    CASE WHEN o.unit = 'Pa' THEN 'hPa' ELSE o.unit END       AS unit
                FROM observations o
                JOIN stations s ON s.id = o.station_id
                WHERE s.station_code  = %s
                  AND o.variable_code = %s
                  AND o.observed_at  >= %s::date
                  AND o.observed_at  <  %s::date + interval '1 day'
                ORDER BY o.observed_at
                LIMIT 5000
            """
            with connection.cursor() as cur:
                cur.execute(sql, [station_code, variable_code, start, end])
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

        trunc_unit = self._AGG_TRUNC.get(agg, "day")
        sql = """
            SELECT
                date_trunc(%s, o.observed_at)                                AS period,
                ROUND(AVG(
                    CASE WHEN o.unit = 'Pa' THEN o.raw_value / 100
                         ELSE o.raw_value END
                )::numeric, 4)                                               AS avg,
                ROUND(MIN(
                    CASE WHEN o.unit = 'Pa' THEN o.raw_value / 100
                         ELSE o.raw_value END
                )::numeric, 4)                                               AS min,
                ROUND(MAX(
                    CASE WHEN o.unit = 'Pa' THEN o.raw_value / 100
                         ELSE o.raw_value END
                )::numeric, 4)                                               AS max,
                COUNT(*)                                                     AS count
            FROM observations o
            JOIN stations s ON s.id = o.station_id
            WHERE s.station_code  = %s
              AND o.variable_code = %s
              AND o.observed_at  >= %s::date
              AND o.observed_at  <  %s::date + interval '1 day'
            GROUP BY period
            ORDER BY period
        """
        with connection.cursor() as cur:
            cur.execute(sql, [trunc_unit, station_code, variable_code, start, end])
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

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