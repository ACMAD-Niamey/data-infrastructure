from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from observations.services.observation_reader import ObservationReader
from stations.models import CountryBoundary

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

STATION_LIST_ROW = {
    "id": 1,
    "station_code": "60390",
    "name": "DAR-EL-BEIDA",
    "country_code": "DZA",
    "admin1": None,
    "admin2": None,
    "station_type": "aws",
    "elevation_m": 25.0,
    "latitude": 36.69,
    "longitude": 3.22,
    "variables_available": ["temp", "rh"],
    "latest_observed_at": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
}

STATION_INFO_ROW = {
    "id": 1,
    "station_code": "60390",
    "name": "DAR-EL-BEIDA",
    "country_code": "DZA",
    "station_type": "aws",
    "is_active": True,
    "elevation_m": 25.0,
    "latitude": 36.69,
    "longitude": 3.22,
    "total_records": 8,
    "first_observation": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
    "last_observation": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
}

STATION_VARIABLES = [
    {
        "variable_code": "temp",
        "unit": "degC",
        "record_count": 4,
        "first_observation": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
        "last_observation": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
    },
    {
        "variable_code": "rh",
        "unit": "%",
        "record_count": 4,
        "first_observation": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
        "last_observation": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
    },
]

AGG_TIME_SERIES = [
    {
        "period": datetime(2026, 4, 27, tzinfo=timezone.utc),
        "avg": 18.1,
        "min": 14.2,
        "max": 24.8,
        "count": 4,
    }
]

RAW_TIME_SERIES = [
    {
        "period": datetime(2026, 4, 27, 7, 0, tzinfo=timezone.utc),
        "value": 18.1,
        "unit": "degC",
    }
]


# ---------------------------------------------------------------------------
# StationListView
# ---------------------------------------------------------------------------

class StationListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("station-list")

    @patch("stations.views.ObservationReader")
    def test_returns_200_with_station_list(self, MockReader):
        mock_reader = MockReader.return_value
        mock_reader.station_list.return_value = [STATION_LIST_ROW]
        mock_reader.station_list_spatial_extent.return_value = {
            "west": 3.0,
            "south": 36.0,
            "east": 4.0,
            "north": 37.0,
        }

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["station_code"], "60390")
        self.assertEqual(response.data["extent"]["west"], 3.0)

    @patch("stations.views.ObservationReader")
    def test_returns_200_with_empty_list(self, MockReader):
        mock_reader = MockReader.return_value
        mock_reader.station_list.return_value = []
        mock_reader.station_list_spatial_extent.return_value = None

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])
        self.assertIsNone(response.data["extent"])

    @patch("stations.views.ObservationReader")
    def test_response_contains_expected_fields(self, MockReader):
        mock_reader = MockReader.return_value
        mock_reader.station_list.return_value = [STATION_LIST_ROW]
        mock_reader.station_list_spatial_extent.return_value = None

        response = self.client.get(self.url)
        item = response.data["results"][0]

        for field in ["station_code", "name", "country_code", "latitude", "longitude",
                      "variables_available", "latest_observed_at"]:
            self.assertIn(field, item)


# ---------------------------------------------------------------------------
# StationFacetsView
# ---------------------------------------------------------------------------


class StationFacetsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("station-facets")

    @patch("stations.views.ObservationReader")
    def test_returns_facets(self, MockReader):
        MockReader.return_value.station_facets.return_value = {
            "countries": [{"value": "DZA", "label": "Algeria"}, {"value": "NER", "label": "Niger"}],
            "admin1": ["Region A"],
        }

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["countries"][0]["value"], "DZA")
        self.assertEqual(response.data["countries"][0]["label"], "Algeria")
        self.assertEqual(response.data["admin1"], ["Region A"])


# ---------------------------------------------------------------------------
# StationDetailView
# ---------------------------------------------------------------------------

class StationDetailViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _url(self, code="60390"):
        return reverse("station-detail", kwargs={"station_code": code})

    @patch("stations.views.ObservationReader")
    def test_returns_200_for_known_station(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.station_variables.return_value = STATION_VARIABLES

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["station_code"], "60390")

    @patch("stations.views.ObservationReader")
    def test_returns_404_for_unknown_station(self, MockReader):
        MockReader.return_value.station_info.return_value = None

        response = self.client.get(self._url("UNKNOWN"))

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.data)

    @patch("stations.views.ObservationReader")
    def test_response_includes_variables(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.station_variables.return_value = STATION_VARIABLES

        response = self.client.get(self._url())

        self.assertIn("variables", response.data)
        self.assertEqual(len(response.data["variables"]), 2)
        self.assertEqual(response.data["variables"][0]["variable_code"], "temp")

    @patch("stations.views.ObservationReader")
    def test_station_variables_called_with_correct_code(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.station_variables.return_value = []

        self.client.get(self._url("60390"))

        instance.station_info.assert_called_once_with("60390")
        instance.station_variables.assert_called_once_with("60390")


# ---------------------------------------------------------------------------
# StationStatsView
# ---------------------------------------------------------------------------

class StationStatsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def _url(self, code="60390"):
        return reverse("station-stats", kwargs={"station_code": code})

    # -- validation ----------------------------------------------------------

    def test_returns_400_when_variable_missing(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 400)
        self.assertIn("variable", response.data["detail"])

    def test_returns_400_for_invalid_agg(self):
        response = self.client.get(self._url(), {"variable": "temp", "agg": "bad_value"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("agg", response.data["detail"].lower())

    # -- 404 -----------------------------------------------------------------

    @patch("stations.views.ObservationReader")
    def test_returns_404_for_unknown_station(self, MockReader):
        MockReader.return_value.station_info.return_value = None

        response = self.client.get(self._url("UNKNOWN"), {"variable": "temp"})

        self.assertEqual(response.status_code, 404)

    # -- aggregated responses ------------------------------------------------

    @patch("stations.views.ObservationReader")
    def test_returns_daily_aggregation_by_default(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = AGG_TIME_SERIES

        response = self.client.get(self._url(), {"variable": "temp"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["aggregation"], "daily")
        self.assertEqual(len(response.data["data"]), 1)
        self.assertIn("avg", response.data["data"][0])

    @patch("stations.views.ObservationReader")
    def test_returns_hourly_aggregation(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = AGG_TIME_SERIES

        response = self.client.get(self._url(), {"variable": "temp", "agg": "hourly"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["aggregation"], "hourly")

    @patch("stations.views.ObservationReader")
    def test_returns_monthly_aggregation(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = AGG_TIME_SERIES

        response = self.client.get(self._url(), {"variable": "temp", "agg": "monthly"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["aggregation"], "monthly")

    @patch("stations.views.ObservationReader")
    def test_returns_yearly_aggregation(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = AGG_TIME_SERIES

        response = self.client.get(self._url(), {"variable": "temp", "agg": "yearly"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["aggregation"], "yearly")

    # -- raw response --------------------------------------------------------

    @patch("stations.views.ObservationReader")
    def test_returns_raw_observations(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = RAW_TIME_SERIES

        response = self.client.get(self._url(), {"variable": "temp", "agg": "raw"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["aggregation"], "raw")
        self.assertIn("value", response.data["data"][0])
        self.assertNotIn("avg", response.data["data"][0])

    # -- reader called correctly ---------------------------------------------

    @patch("stations.views.ObservationReader")
    def test_reader_called_with_correct_params(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = AGG_TIME_SERIES

        self.client.get(
            self._url(),
            {"variable": "rh", "agg": "monthly", "start": "2026-01-01", "end": "2026-04-30"},
        )

        instance.time_series_by_station_code.assert_called_once_with(
            station_code="60390",
            variable_code="rh",
            start="2026-01-01",
            end="2026-04-30",
            agg="monthly",
        )

    # -- payload structure ---------------------------------------------------

    @patch("stations.views.ObservationReader")
    def test_payload_contains_expected_top_level_keys(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = AGG_TIME_SERIES

        response = self.client.get(self._url(), {"variable": "temp"})

        for key in ["station_code", "station_name", "variable", "aggregation", "start", "end", "data"]:
            self.assertIn(key, response.data)

    @patch("stations.views.ObservationReader")
    def test_empty_data_returns_200(self, MockReader):
        instance = MockReader.return_value
        instance.station_info.return_value = dict(STATION_INFO_ROW)
        instance.time_series_by_station_code.return_value = []

        response = self.client.get(self._url(), {"variable": "temp"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], [])


# ---------------------------------------------------------------------------
# CountryBoundsView  GET /api/stations/country-bounds/
# ---------------------------------------------------------------------------


def _minimal_country_geom() -> MultiPolygon:
    ring = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))
    return MultiPolygon(Polygon(ring))


class CountryBoundsOptionsTests(TestCase):
    """country_bounds_options reads CountryBoundary only (no observations join)."""

    def test_returns_rows_with_bounds_and_code_ordered_by_name(self):
        CountryBoundary.objects.create(
            country_name="Beta Land",
            country_code="BBB",
            geom=_minimal_country_geom(),
            country_bounds={"west": 0.0, "south": 0.0, "east": 1.0, "north": 1.0},
        )
        CountryBoundary.objects.create(
            country_name="Alpha Land",
            country_code="AAA",
            geom=_minimal_country_geom(),
            country_bounds={"west": 2.0, "south": 2.0, "east": 3.0, "north": 3.0},
        )
        CountryBoundary.objects.create(
            country_name="No Bounds",
            country_code="NB",
            geom=_minimal_country_geom(),
            country_bounds=None,
        )
        CountryBoundary.objects.create(
            country_name="No Code",
            country_code="",
            geom=_minimal_country_geom(),
            country_bounds={"west": 0.0, "south": 0.0, "east": 1.0, "north": 1.0},
        )

        options = ObservationReader().country_bounds_options()
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0]["label"], "Alpha Land")
        self.assertEqual(options[0]["value"], "AAA")
        self.assertEqual(options[1]["label"], "Beta Land")
        self.assertEqual(options[1]["value"], "BBB")
        for opt in options:
            self.assertIn("bounds", opt)
            for k in ("west", "south", "east", "north"):
                self.assertIn(k, opt["bounds"])


class CountryBoundsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_returns_200_and_expected_keys_without_observations(self):
        CountryBoundary.objects.create(
            country_name="Test Country",
            country_code="TST",
            geom=_minimal_country_geom(),
            country_bounds={"west": 10.0, "south": -5.0, "east": 11.0, "north": -4.0},
        )
        response = self.client.get("/api/stations/country-bounds/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertEqual(row["value"], "TST")
        self.assertEqual(row["label"], "Test Country")
        self.assertEqual(row["bounds"]["west"], 10.0)
        self.assertEqual(row["bounds"]["east"], 11.0)
