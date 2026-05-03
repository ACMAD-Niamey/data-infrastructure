from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import connection
from stations.models import CountryBoundary


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
        "yearly": "year",
    }

    def station_info(self, station_code: str) -> dict | None:
        """Return basic metadata for a single station plus per-variable counts."""
        sql = """
            SELECT
                s.id,
                s.station_code,
                s.name,
                s.country_code,
                s.country_name,
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
            GROUP BY s.id, s.station_code, s.name, s.country_code, s.country_name,
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

    @staticmethod
    def _station_geo_filter_sql(
        country_code: str | None,
        admin1: str | None,
        admin2: str | None,
    ) -> tuple[str, list[Any]]:
        """Returns fragment `` AND ...`` plus bind params for stations alias ``s``."""
        parts: list[str] = []
        params: list[Any] = []
        if country_code and country_code.strip():
            parts.append("s.canonical_code = %s")
            params.append(country_code.strip().upper())
        if admin1 and admin1.strip():
            parts.append("s.admin1 = %s")
            params.append(admin1.strip())
        if admin2 and admin2.strip():
            parts.append("s.admin2 = %s")
            params.append(admin2.strip())
        if not parts:
            return "", []
        return " AND " + " AND ".join(parts), params

    def station_list(
        self,
        *,
        country_code: str | None = None,
        admin1: str | None = None,
        admin2: str | None = None,
    ) -> list[dict]:
        """
        Return active stations that have at least one observation,
        with variable codes and latest observation time.

        Optional filters narrow by ISO country code (alpha-3), admin1, admin2 (exact match).
        """
        extra_sql, extra_params = self._station_geo_filter_sql(country_code, admin1, admin2)
        sql = f"""
            SELECT
                s.id,
                s.station_code,
                s.name,
                s.country_code,
                s.country_name,
                s.admin1,
                s.admin2,
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
              {extra_sql}
            GROUP BY s.id, s.station_code, s.name, s.country_code, s.country_name,
                     s.admin1, s.admin2,
                     s.station_type, s.elevation_m, s.geom
            ORDER BY s.country_code, s.name
        """
        with connection.cursor() as cur:
            cur.execute(sql, extra_params)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def station_list_spatial_extent(
        self,
        *,
        country_code: str | None = None,
        admin1: str | None = None,
        admin2: str | None = None,
    ) -> dict[str, float] | None:
        """
        Bounding box (WGS84 degrees) for stations matching the same filters as station_list,
        or None if no stations match.
        """
        extra_sql, extra_params = self._station_geo_filter_sql(country_code, admin1, admin2)
        sql = f"""
            SELECT
                ST_XMin(box) AS west,
                ST_YMin(box) AS south,
                ST_XMax(box) AS east,
                ST_YMax(box) AS north
            FROM (
                SELECT ST_Extent(s.geom::geometry) AS box
                FROM stations s
                JOIN observations o ON o.station_id = s.id
                WHERE s.is_active = TRUE
                  AND s.geom IS NOT NULL
                  {extra_sql}
            ) t
            WHERE box IS NOT NULL
        """
        with connection.cursor() as cur:
            cur.execute(sql, extra_params)
            row = cur.fetchone()
            if row is None or row[0] is None:
                return None
            west, south, east, north = row
            return {
                "west": float(west),
                "south": float(south),
                "east": float(east),
                "north": float(north),
            }

    def station_facets(self, *, country_code: str | None = None) -> dict[str, Any]:
        """Distinct country/admin1 values for stations that have observations."""
        sql = """
            SELECT
                MIN(s.canonical_code) AS canonical_code,
                TRIM(s.country_name) AS country_name
            FROM stations s
            JOIN observations o ON o.station_id = s.id
            WHERE s.is_active = TRUE
              AND s.geom IS NOT NULL
              AND s.canonical_code IS NOT NULL
              AND s.canonical_code <> ''
              AND s.country_name IS NOT NULL
              AND TRIM(s.country_name) <> ''
            GROUP BY TRIM(s.country_name)
            ORDER BY TRIM(s.country_name)
        """
        with connection.cursor() as cur:
            cur.execute(sql)
            countries = [
                {"value": code, "label": name}
                for code, name in cur.fetchall()
                if code and name
            ]

        admin1_params: list[Any] = []
        admin1_filter_sql = ""
        if country_code and country_code.strip():
            admin1_filter_sql = " AND s.canonical_code = %s"
            admin1_params.append(country_code.strip().upper())

        with connection.cursor() as cur:
            cur.execute(
                f"""
                SELECT DISTINCT s.admin1
                FROM stations s
                JOIN observations o ON o.station_id = s.id
                WHERE s.is_active = TRUE
                  AND s.geom IS NOT NULL
                  AND s.admin1 IS NOT NULL
                  AND TRIM(s.admin1) <> ''
                  {admin1_filter_sql}
                ORDER BY 1
                """,
                admin1_params,
            )
            regions = [r[0] for r in cur.fetchall() if r[0]]

        return {
            "countries": countries,
            "admin1": regions,
        }

    def country_bounds_options(self) -> list[dict[str, Any]]:
        """
        Countries with map zoom bounds from ``country_boundaries`` only.

        Does not query stations or observations; rows without ``country_bounds``
        or usable ``country_code`` are omitted.
        """
        qs = (
            CountryBoundary.objects.filter(country_bounds__isnull=False)
            .exclude(country_code__isnull=True)
            .exclude(country_code="")
            .values("country_code", "country_name", "country_bounds")
            .order_by("country_name")
        )
        options: list[dict[str, Any]] = []
        for row in qs:
            code_raw = row.get("country_code") or ""
            label_raw = row.get("country_name") or ""
            bounds = row.get("country_bounds")
            code = code_raw.strip().upper()
            label = label_raw.strip()
            if not code or not label or not bounds:
                continue
            options.append({"value": code, "label": label, "bounds": bounds})
        return options

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
                s.country_name,
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