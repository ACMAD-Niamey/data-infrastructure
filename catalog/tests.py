from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pgstac_cursor(dates, min_d=None, max_d=None):
    """
    Return a mock context-manager cursor whose first fetchone() returns
    (min_d, max_d) and fetchall() returns the supplied dates.
    """
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: mock_cursor
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = (min_d, max_d)
    mock_cursor.fetchall.return_value = [(d,) for d in dates]
    return mock_cursor


def _make_layer(layer_id="spi-layer", dataset_id="spi"):
    mock_dataset = MagicMock()
    mock_dataset.dataset_id = dataset_id
    mock_dataset.title = dataset_id.upper()
    mock_dataset.cadence = "monthly"
    mock_dataset.dataset_type = "raster"
    mock_dataset.stac_collection_id = dataset_id
    mock_dataset.is_published_for_ui = True
    mock_dataset.get_parent.return_value = MagicMock(slug="acmad")

    mock_lyr = MagicMock()
    mock_lyr.layer_id = layer_id
    mock_lyr.title = "Test Layer"
    mock_lyr.layer_type = "raster"
    mock_lyr.dataset = mock_dataset
    mock_lyr.tile_template = "/tiles/{z}/{x}/{y}"
    mock_lyr.tile_params = {}
    mock_lyr.default_visible = True
    mock_lyr.opacity = 0.85
    mock_lyr.minzoom = 0
    mock_lyr.maxzoom = 12
    mock_lyr.legend = {}
    mock_lyr.updated_at.isoformat.return_value = "2026-04-28T00:00:00"
    return mock_lyr


# ---------------------------------------------------------------------------
# UILayersView  GET /api/catalog/ui/layers
# ---------------------------------------------------------------------------


class UILayersViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("catalog.api.Layer")
    def test_returns_200_with_published_layers(self, mock_layer_cls):
        mock_layer_cls.objects.select_related.return_value.filter.return_value.order_by.return_value = [
            _make_layer()
        ]
        response = self.client.get("/api/catalog/ui/layers")
        self.assertEqual(response.status_code, 200)
        self.assertIn("layers", response.data)
        self.assertEqual(len(response.data["layers"]), 1)

    @patch("catalog.api.Layer")
    def test_returns_200_with_empty_layer_list(self, mock_layer_cls):
        mock_layer_cls.objects.select_related.return_value.filter.return_value.order_by.return_value = []
        response = self.client.get("/api/catalog/ui/layers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["layers"], [])

    @patch("catalog.api.Layer")
    def test_response_contains_version_and_layers_keys(self, mock_layer_cls):
        mock_layer_cls.objects.select_related.return_value.filter.return_value.order_by.return_value = []
        response = self.client.get("/api/catalog/ui/layers")
        self.assertIn("version", response.data)
        self.assertIn("layers", response.data)

    @patch("catalog.api.Layer")
    def test_layer_item_contains_expected_fields(self, mock_layer_cls):
        mock_layer_cls.objects.select_related.return_value.filter.return_value.order_by.return_value = [
            _make_layer("ndvi-layer", "ndvi")
        ]
        response = self.client.get("/api/catalog/ui/layers")
        layer = response.data["layers"][0]
        for field in ("id", "title", "type", "dataset", "tile", "ui", "legend"):
            self.assertIn(field, layer)


# ---------------------------------------------------------------------------
# DatasetAvailabilityView  GET /api/catalog/datasets/<dataset_id>/availability/
# ---------------------------------------------------------------------------


class DatasetAvailabilityViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("catalog.views.connections")
    def test_daily_cadence_returns_iso_date_strings(self, mock_conns):
        dates = [date(2026, 4, 1), date(2026, 4, 2)]
        cur = _make_pgstac_cursor(dates, min_d=date(2026, 4, 1), max_d=date(2026, 4, 2))
        mock_conns.__getitem__.return_value.cursor.return_value = cur

        response = self.client.get("/api/catalog/datasets/spi/availability/?cadence=daily")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["available"], ["2026-04-01", "2026-04-02"])

    @patch("catalog.views.connections")
    def test_monthly_cadence_returns_year_month_strings(self, mock_conns):
        dates = [date(2026, 1, 15), date(2026, 2, 10)]
        cur = _make_pgstac_cursor(dates, min_d=date(2026, 1, 15), max_d=date(2026, 2, 10))
        mock_conns.__getitem__.return_value.cursor.return_value = cur

        response = self.client.get("/api/catalog/datasets/spi/availability/?cadence=monthly")
        self.assertEqual(response.status_code, 200)
        self.assertIn("2026-01", response.data["available"])
        self.assertIn("2026-02", response.data["available"])

    @patch("catalog.views.connections")
    def test_dekadal_cadence_maps_to_dekad_start_dates(self, mock_conns):
        # day 5 -> 1st, day 15 -> 11th, day 25 -> 21st
        dates = [date(2026, 4, 5), date(2026, 4, 15), date(2026, 4, 25)]
        cur = _make_pgstac_cursor(dates, min_d=date(2026, 4, 5), max_d=date(2026, 4, 25))
        mock_conns.__getitem__.return_value.cursor.return_value = cur

        response = self.client.get("/api/catalog/datasets/spi/availability/?cadence=dekadal")
        self.assertEqual(response.status_code, 200)
        available = response.data["available"]
        self.assertIn("2026-04-01", available)
        self.assertIn("2026-04-11", available)
        self.assertIn("2026-04-21", available)

    @patch("catalog.views.connections")
    def test_no_items_returns_empty_available_list(self, mock_conns):
        cur = _make_pgstac_cursor([], min_d=None, max_d=None)
        mock_conns.__getitem__.return_value.cursor.return_value = cur

        response = self.client.get("/api/catalog/datasets/empty-ds/availability/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["available"], [])

    def test_invalid_cadence_returns_400(self):
        response = self.client.get("/api/catalog/datasets/spi/availability/?cadence=weekly")
        self.assertEqual(response.status_code, 400)

    @patch("catalog.views.connections")
    def test_response_echoes_dataset_id_and_cadence(self, mock_conns):
        dates = [date(2026, 4, 1)]
        cur = _make_pgstac_cursor(dates, min_d=date(2026, 4, 1), max_d=date(2026, 4, 1))
        mock_conns.__getitem__.return_value.cursor.return_value = cur

        response = self.client.get("/api/catalog/datasets/cdi/availability/?cadence=daily")
        self.assertEqual(response.data["dataset_id"], "cdi")
        self.assertEqual(response.data["cadence"], "daily")


# ---------------------------------------------------------------------------
# DatasetVisualizationView  GET /api/catalog/datasets/<dataset_id>/visualization/
# ---------------------------------------------------------------------------


class DatasetVisualizationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("catalog.views.DatasetVisualization")
    def test_returns_200_with_titiler_info(self, mock_viz_cls):
        mock_viz = MagicMock()
        mock_viz.cadence = "monthly"
        mock_viz.legend_dict = {"type": "linear", "min": 0, "max": 1}
        mock_viz.get_visualization.return_value = {"tiles": "http://titiler/tiles/{z}/{x}/{y}"}
        mock_viz_cls.return_value = mock_viz

        response = self.client.get(
            "/api/catalog/datasets/spi/visualization/?date=2026-04&cadence=monthly"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("titiler_url", response.data)
        self.assertIn("titiler_info", response.data)
        self.assertIn("dataset_id", response.data)

    @patch("catalog.views.DatasetVisualization")
    def test_returns_404_when_no_visualization_available(self, mock_viz_cls):
        mock_viz = MagicMock()
        mock_viz.get_visualization.return_value = None
        mock_viz_cls.return_value = mock_viz

        response = self.client.get(
            "/api/catalog/datasets/spi/visualization/?date=2026-04&cadence=monthly"
        )
        self.assertEqual(response.status_code, 404)

    @patch("catalog.views.DatasetVisualization")
    def test_returns_400_on_value_error_from_visualization(self, mock_viz_cls):
        mock_viz_cls.side_effect = ValueError("invalid date format")

        response = self.client.get(
            "/api/catalog/datasets/spi/visualization/?date=2026-04&cadence=monthly"
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_required_date_param_returns_400(self):
        response = self.client.get(
            "/api/catalog/datasets/spi/visualization/?cadence=monthly"
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_required_cadence_param_returns_400(self):
        response = self.client.get(
            "/api/catalog/datasets/spi/visualization/?date=2026-04"
        )
        self.assertEqual(response.status_code, 400)
