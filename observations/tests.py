import importlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

# Migration modules start with a digit, so they aren't importable via
# `from x import y` -- load by dotted path instead.
_tablespace_migration = importlib.import_module(
    "observations.migrations.0003_move_observations_to_hdd_tablespace"
)

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

OBS_ROW = {
    "station_id": 1,
    "sensor_id": None,
    "dataset_id": 2,
    "source_id": 3,
    "observed_at": datetime(2026, 4, 28, 6, 0, tzinfo=timezone.utc),
    "variable_code": "temp",
    "raw_value": 23.5,
    "cleaned_value": 23.5,
    "unit": "degC",
    "qc_flag": "ok",
    "qc_notes": None,
    "ingest_time": datetime(2026, 4, 28, 6, 5, tzinfo=timezone.utc),
    "payload_ref": None,
}

# ---------------------------------------------------------------------------
# LatestObservationsAPIView  GET /api/observations/latest/
# ---------------------------------------------------------------------------


class LatestObservationsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("observations.views.ObservationReader")
    def test_returns_200_with_data(self, mock_cls):
        mock_cls.return_value.latest.return_value = [OBS_ROW]
        response = self.client.get("/api/observations/latest/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    @patch("observations.views.ObservationReader")
    def test_default_limit_is_10(self, mock_cls):
        mock_cls.return_value.latest.return_value = []
        self.client.get("/api/observations/latest/")
        mock_cls.return_value.latest.assert_called_once_with(limit=10)

    @patch("observations.views.ObservationReader")
    def test_limit_param_is_respected(self, mock_cls):
        mock_cls.return_value.latest.return_value = []
        self.client.get("/api/observations/latest/?limit=25")
        mock_cls.return_value.latest.assert_called_once_with(limit=25)

    @patch("observations.views.ObservationReader")
    def test_response_contains_expected_fields(self, mock_cls):
        mock_cls.return_value.latest.return_value = [OBS_ROW]
        response = self.client.get("/api/observations/latest/")
        record = response.data[0]
        for field in ("station_id", "variable_code", "raw_value", "unit", "observed_at"):
            self.assertIn(field, record)


# ---------------------------------------------------------------------------
# StationObservationsAPIView  GET /api/observations/station/<int:station_id>/
# ---------------------------------------------------------------------------


class StationObservationsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("observations.views.ObservationReader")
    def test_returns_200_for_station(self, mock_cls):
        mock_cls.return_value.by_station.return_value = [OBS_ROW]
        response = self.client.get("/api/observations/station/1/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    @patch("observations.views.ObservationReader")
    def test_reader_called_with_correct_station_id(self, mock_cls):
        mock_cls.return_value.by_station.return_value = []
        self.client.get("/api/observations/station/42/")
        mock_cls.return_value.by_station.assert_called_once_with(station_id=42, limit=100)

    @patch("observations.views.ObservationReader")
    def test_limit_param_is_respected(self, mock_cls):
        mock_cls.return_value.by_station.return_value = []
        self.client.get("/api/observations/station/1/?limit=50")
        mock_cls.return_value.by_station.assert_called_once_with(station_id=1, limit=50)


# ---------------------------------------------------------------------------
# VariableObservationsAPIView  GET /api/observations/variable/<str:variable_code>/
# ---------------------------------------------------------------------------


class VariableObservationsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("observations.views.ObservationReader")
    def test_returns_200_for_variable(self, mock_cls):
        mock_cls.return_value.by_variable.return_value = [OBS_ROW]
        response = self.client.get("/api/observations/variable/temp/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    @patch("observations.views.ObservationReader")
    def test_reader_called_with_correct_variable_code(self, mock_cls):
        mock_cls.return_value.by_variable.return_value = []
        self.client.get("/api/observations/variable/rh/")
        mock_cls.return_value.by_variable.assert_called_once_with(variable_code="rh", limit=100)


# ---------------------------------------------------------------------------
# ObservationStatsAPIView  GET /api/observations/stats/
# ---------------------------------------------------------------------------


class ObservationStatsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("observations.views.ObservationStatsReader")
    def test_returns_200_with_stats(self, mock_cls):
        mock_cls.return_value.count_by_variable.return_value = [("temp", 100)]
        mock_cls.return_value.total_count.return_value = 100
        mock_cls.return_value.latest_timestamp.return_value = datetime(
            2026, 4, 28, 6, 0, tzinfo=timezone.utc
        )
        response = self.client.get("/api/observations/stats/")
        self.assertEqual(response.status_code, 200)

    @patch("observations.views.ObservationStatsReader")
    def test_response_contains_total_count(self, mock_cls):
        mock_cls.return_value.count_by_variable.return_value = []
        mock_cls.return_value.total_count.return_value = 42
        mock_cls.return_value.latest_timestamp.return_value = None
        response = self.client.get("/api/observations/stats/")
        self.assertIn("total_count", response.data)
        self.assertEqual(response.data["total_count"], 42)

    @patch("observations.views.ObservationStatsReader")
    def test_response_contains_by_variable_breakdown(self, mock_cls):
        mock_cls.return_value.count_by_variable.return_value = [("temp", 50), ("rh", 30)]
        mock_cls.return_value.total_count.return_value = 80
        mock_cls.return_value.latest_timestamp.return_value = None
        response = self.client.get("/api/observations/stats/")
        self.assertIn("by_variable", response.data)
        codes = [item["variable_code"] for item in response.data["by_variable"]]
        self.assertIn("temp", codes)
        self.assertIn("rh", codes)


# ---------------------------------------------------------------------------
# 0003_move_observations_to_hdd_tablespace -- unit tests against a mocked
# cursor. CREATE TABLESPACE's LOCATION must exist on whatever host the
# Postgres *server* process runs, which (split web/db containers) isn't
# something a portable test can rely on -- so these verify the control flow
# (idempotency checks, skip-on-failure) rather than a real filesystem move;
# that path is exercised manually (see PR description).
# ---------------------------------------------------------------------------


def _mock_cursor(fetchone_results):
    """A `with connection.cursor() as cursor:` mock whose fetchone() returns
    each of `fetchone_results` in order across successive SELECTs."""
    cursor = MagicMock()
    cursor.fetchone.side_effect = fetchone_results
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


class MoveObservationsToHddTablespaceTests(TestCase):
    def test_creates_tablespace_and_moves_table_when_missing(self):
        # tablespace doesn't exist yet; observations is on pg_default
        conn, cursor = _mock_cursor([None, ("pg_default",)])
        with patch("django.db.connection", conn):
            _tablespace_migration.move_observations_to_hdd_tablespace(None, None)

        executed = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("CREATE TABLESPACE" in sql for sql in executed))
        self.assertTrue(any("ALTER TABLE observations SET TABLESPACE" in sql for sql in executed))

    def test_skips_when_tablespace_creation_fails(self):
        # LOCATION not mounted/writable in this environment (local dev, CI)
        conn, cursor = _mock_cursor([None])
        cursor.execute.side_effect = [None, Exception("could not create directory")]
        with patch("django.db.connection", conn):
            _tablespace_migration.move_observations_to_hdd_tablespace(None, None)

        executed = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any("ALTER TABLE observations SET TABLESPACE" in sql for sql in executed))

    def test_noop_when_already_on_target_tablespace(self):
        conn, cursor = _mock_cursor([(1,), (_tablespace_migration.TABLESPACE_NAME,)])
        with patch("django.db.connection", conn):
            _tablespace_migration.move_observations_to_hdd_tablespace(None, None)

        executed = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any("CREATE TABLESPACE" in sql for sql in executed))
        self.assertFalse(any("ALTER TABLE observations SET TABLESPACE" in sql for sql in executed))

    def test_reverse_moves_back_to_default_only_if_on_hdd(self):
        conn, cursor = _mock_cursor([(_tablespace_migration.TABLESPACE_NAME,)])
        with patch("django.db.connection", conn):
            _tablespace_migration.move_observations_back_to_default(None, None)

        executed = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("SET TABLESPACE pg_default" in sql for sql in executed))

    def test_reverse_noop_when_already_on_default(self):
        conn, cursor = _mock_cursor([("pg_default",)])
        with patch("django.db.connection", conn):
            _tablespace_migration.move_observations_back_to_default(None, None)

        cursor.execute.assert_called_once()  # only the SELECT, no ALTER
