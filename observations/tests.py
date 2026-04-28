from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

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
