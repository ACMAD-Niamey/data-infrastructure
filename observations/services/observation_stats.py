from __future__ import annotations

from django.db import connection


class ObservationStatsReader:
    def total_count(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM observations")
            return cursor.fetchone()[0]

    def count_by_variable(self) -> list[tuple[str, int]]:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT variable_code, COUNT(*)
                FROM observations
                GROUP BY variable_code
                ORDER BY COUNT(*) DESC
            """)
            return cursor.fetchall()

    def latest_timestamp(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(observed_at) FROM observations")
            return cursor.fetchone()[0]