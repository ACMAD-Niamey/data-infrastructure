import json
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.datastructures import MultiValueDict

from catalog.models import Layer, LayerColorStop
from catalog.style.band_defaults import (
    DEFAULT_RGB_BAND_VISUALIZATION_PARAMS,
    ensure_band_tile_params,
)
from catalog.style.normalize import normalize_tile_params
from catalog.widgets import HexColorWidget, LegendMapWidget
from catalog.widgets.hex_color import hex_for_color_input
from catalog.widgets.legend_map import (
    entries_to_legend,
    is_simple_name_color_legend,
    legend_to_entries,
)
from catalog.style.parse_qml import parse_qml_raster_pseudocolor
from catalog.style.parse_sld import parse_sld_raster_colormap
from catalog.style.titiler_export import (
    build_colormap_for_titiler,
    compose_titiler_tilejson_params,
)
from catalog.ui_layers import DatasetEntry, dataset_description_payload


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


def _make_dataset(dataset_id="spi", project_slug="e-safari", with_style=False):
    mock_dataset = MagicMock()
    mock_dataset.dataset_id = dataset_id
    mock_dataset.title = dataset_id.upper()
    mock_dataset.cadence = "monthly"
    mock_dataset.dataset_type = "raster"
    mock_dataset.stac_collection_id = dataset_id
    mock_dataset.is_published_for_ui = True
    mock_dataset.description = None
    mock_dataset.color_class = "text-blue-600"
    mock_dataset.hazard_category_id = None
    mock_dataset.get_parent.return_value = MagicMock(slug=project_slug)
    mock_dataset.last_published_at = None

    mock_icon_image = MagicMock()
    mock_icon_image.file.url = "/media/icons/test.png"

    mock_icon = MagicMock()
    mock_icon.slug = "test-icon"
    mock_icon.image = mock_icon_image
    mock_icon.image_id = 1

    mock_dataset.icon = mock_icon
    mock_dataset.icon_id = 1

    if with_style:
        mock_style = MagicMock()
        mock_style.layer_type = "raster"
        mock_style.tile_template = "/tiles/{z}/{x}/{y}"
        mock_style.tile_params = {}
        mock_style.default_visible = True
        mock_style.opacity = 0.85
        mock_style.minzoom = 0
        mock_style.maxzoom = 12
        mock_style.legend = {"low": "#0000ff", "high": "#ff0000"}
        mock_style.updated_at.isoformat.return_value = "2026-04-28T00:00:00"
        # Set all string detail fields explicitly — MagicMock is truthy so
        # `mock.field or "fallback"` returns the mock, not the fallback.
        # expand_db_html also fails if it receives a MagicMock instead of a str.
        mock_style.coverage = "Africa"
        mock_style.resolution = ""
        mock_style.update_frequency = ""
        mock_style.source_organization = ""
        mock_style.methodology = None
        mock_style.methodology_url = ""
        mock_dataset.style_config = mock_style
    else:
        mock_dataset.style_config = None

    return mock_dataset


# ---------------------------------------------------------------------------
# dataset_description_payload
# ---------------------------------------------------------------------------


class DatasetDescriptionPayloadTests(unittest.TestCase):
    def test_empty_description(self):
        dataset = MagicMock()
        dataset.description = None
        self.assertEqual(dataset_description_payload(dataset), {"html": "", "plain": ""})

    def test_plain_string_description(self):
        dataset = MagicMock()
        dataset.description = "<p>Remote sensing overview</p>"
        payload = dataset_description_payload(dataset)
        self.assertIn("Remote sensing", payload["plain"])
        self.assertIn("Remote sensing", payload["html"])

    def test_richtext_object_description(self):
        dataset = MagicMock()
        rich = MagicMock()
        rich.source = "<p>From RichText source</p>"
        dataset.description = rich
        payload = dataset_description_payload(dataset)
        self.assertEqual(payload["plain"], "From RichText source")


# ---------------------------------------------------------------------------
# UILayersView  GET /api/catalog/ui/layers
# ---------------------------------------------------------------------------


class UILayersViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_requires_project_query_param(self):
        response = self.client.get("/api/catalog/ui/layers")
        self.assertEqual(response.status_code, 400)
        self.assertIn("project", response.data["detail"])

    @patch("catalog.api.ProjectPage")
    @patch("catalog.api.dataset_entries_for_project")
    def test_returns_200_with_published_layers(self, mock_entries, mock_project_page):
        mock_project_page.objects.live.return_value.filter.return_value.exists.return_value = True
        mock_entries.return_value = [DatasetEntry(_make_dataset(), None)]
        response = self.client.get("/api/catalog/ui/layers?project=e-safari")
        self.assertEqual(response.status_code, 200)
        self.assertIn("layers", response.data)
        self.assertEqual(response.data["project"], "e-safari")
        self.assertEqual(len(response.data["layers"]), 1)

    @patch("catalog.api.ProjectPage")
    @patch("catalog.api.dataset_entries_for_project")
    def test_returns_200_with_empty_layer_list(self, mock_entries, mock_project_page):
        mock_project_page.objects.live.return_value.filter.return_value.exists.return_value = True
        mock_entries.return_value = []
        response = self.client.get("/api/catalog/ui/layers?project=e-safari")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["layers"], [])

    @patch("catalog.api.ProjectPage")
    @patch("catalog.api.dataset_entries_for_project")
    def test_response_contains_version_and_layers_keys(self, mock_entries, mock_project_page):
        mock_project_page.objects.live.return_value.filter.return_value.exists.return_value = True
        mock_entries.return_value = []
        response = self.client.get("/api/catalog/ui/layers?project=e-safari")
        self.assertIn("version", response.data)
        self.assertIn("project", response.data)
        self.assertIn("layers", response.data)

    @patch("catalog.api.ProjectPage")
    @patch("catalog.api.dataset_entries_for_project")
    def test_layer_item_uses_dataset_id_and_includes_icon(self, mock_entries, mock_project_page):
        mock_project_page.objects.live.return_value.filter.return_value.exists.return_value = True
        mock_entries.return_value = [DatasetEntry(_make_dataset("ndvi"), None)]
        response = self.client.get("/api/catalog/ui/layers?project=e-safari")
        layer = response.data["layers"][0]
        self.assertEqual(layer["id"], "ndvi")
        self.assertEqual(layer["dataset"]["id"], "ndvi")
        for field in (
            "id",
            "title",
            "type",
            "description",
            "icon",
            "dataset",
            "selection",
            "tile",
            "ui",
            "legend",
        ):
            self.assertIn(field, layer)
        self.assertIn("url", layer["icon"])
        self.assertIn("plain", layer["description"])

    @patch("catalog.api.ProjectPage")
    @patch("catalog.api.dataset_entries_for_project")
    def test_style_config_merges_legend(self, mock_entries, mock_project_page):
        mock_project_page.objects.live.return_value.filter.return_value.exists.return_value = True
        mock_entries.return_value = [DatasetEntry(_make_dataset("spi", with_style=True), None)]
        response = self.client.get("/api/catalog/ui/layers?project=e-safari")
        layer = response.data["layers"][0]
        self.assertEqual(layer["legend"], {"low": "#0000ff", "high": "#ff0000"})
        self.assertEqual(layer["tile"]["template"], "/tiles/{z}/{x}/{y}")

    @patch("catalog.api.ProjectPage")
    def test_unknown_project_returns_404(self, mock_project_page):
        mock_project_page.objects.live.return_value.filter.return_value.exists.return_value = False
        response = self.client.get("/api/catalog/ui/layers?project=missing")
        self.assertEqual(response.status_code, 404)


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


# ---------------------------------------------------------------------------
# Hex color widget (Wagtail layer color stops)
# ---------------------------------------------------------------------------


class HexColorWidgetTests(unittest.TestCase):
    def test_render_includes_picker_swatch_and_text_name(self):
        html = HexColorWidget().render("color", "#ff00aa", attrs={"id": "id_color"})
        self.assertIn('data-hex-color-widget', html)
        self.assertIn('type="color"', html)
        self.assertIn('name="color"', html)
        self.assertIn('class="hex-color-text"', html)
        self.assertIn("#ff00aa", html)

    def test_hex_for_color_input_empty_defaults_black(self):
        self.assertEqual(hex_for_color_input(None), "#000000")
        self.assertEqual(hex_for_color_input(""), "#000000")

    def test_hex_for_color_input_valid(self):
        self.assertEqual(hex_for_color_input("#AABBCC"), "#aabbcc")


class LayerColorStopForm(ModelForm):
    class Meta:
        model = LayerColorStop
        fields = ["value", "color"]
        widgets = {"color": HexColorWidget()}


class LayerColorStopColorValidationTests(unittest.TestCase):
    def test_valid_hex_passes(self):
        form = LayerColorStopForm(data={"value": 1.0, "color": "#FF00AA"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_hex_fails(self):
        form = LayerColorStopForm(data={"value": 1.0, "color": "red"})
        self.assertFalse(form.is_valid())
        self.assertIn("color", form.errors)

    def test_model_color_field_rejects_invalid_hex(self):
        field = LayerColorStop._meta.get_field("color")
        with self.assertRaises(ValidationError):
            field.clean("not-a-hex", LayerColorStop())


# ---------------------------------------------------------------------------
# Legend map widget (label -> #RRGGBB)
# ---------------------------------------------------------------------------


class LegendMapWidgetHelperTests(unittest.TestCase):
    def test_simple_legend_detected(self):
        self.assertTrue(is_simple_name_color_legend({}))
        self.assertTrue(is_simple_name_color_legend({"Low": "#ff0000", "High": "#00ff00"}))

    def test_structured_legend_not_simple(self):
        self.assertFalse(
            is_simple_name_color_legend(
                {"type": "continuous", "colors": ["#ff0000"], "breaks": [0, 100]}
            )
        )

    def test_legend_to_entries_and_back(self):
        data = {"Dry": "#aabbcc", "Wet": "#112233"}
        entries = legend_to_entries(data)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries_to_legend(entries), data)

    def test_render_includes_rows_and_hidden_json(self):
        html = LegendMapWidget().render(
            "legend",
            {"Low": "#d73027", "High": "#1a9850"},
            attrs={"id": "id_legend"},
        )
        self.assertIn("data-legend-map-widget", html)
        self.assertIn("legend-map-json-hidden", html)
        self.assertIn("Low", html)
        self.assertIn("#d73027", html)
        self.assertIn("data-hex-color-widget", html)
        self.assertIn("data-legend-map-template", html)

    def test_value_from_datadict_returns_json_string(self):
        widget = LegendMapWidget()
        data = MultiValueDict({"legend": ['{"Low":"#ff0000"}']})
        result = widget.value_from_datadict(data, {}, "legend")
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), {"Low": "#ff0000"})

    def test_value_from_datadict_empty_returns_empty_object_string(self):
        widget = LegendMapWidget()
        data = MultiValueDict({"legend": [""]})
        result = widget.value_from_datadict(data, {}, "legend")
        self.assertEqual(result, "{}")


class LegendMapWidgetJSONFieldTests(unittest.TestCase):
    def test_bound_field_value_after_invalid_submit(self):
        class TestForm(forms.Form):
            legend = forms.JSONField(widget=LegendMapWidget())
            title = forms.CharField(required=True)

        form = TestForm(data={"legend": '{"Low":"#ff0000"}', "title": ""})
        self.assertFalse(form.is_valid())
        # prepare_value serializes for the widget; must not raise TypeError from bound_data
        displayed = form["legend"].value()
        self.assertIsInstance(displayed, str)
        self.assertEqual(json.loads(displayed), {"Low": "#ff0000"})

    def test_valid_submit_parses_legend(self):
        class TestForm(forms.Form):
            legend = forms.JSONField(widget=LegendMapWidget())

        form = TestForm(data={"legend": '{"A":"#aabbcc"}'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["legend"], {"A": "#aabbcc"})


class LayerLegendCleanTests(unittest.TestCase):
    def test_clean_coerces_none_json_fields_to_empty_dict(self):
        layer = Layer(title="Test", layer_type="raster", legend=None, tile_params=None)
        layer.clean()
        self.assertEqual(layer.legend, {})
        self.assertEqual(layer.tile_params, {})


# ---------------------------------------------------------------------------
# Band scheme defaults
# ---------------------------------------------------------------------------


class EnsureBandTileParamsTests(unittest.TestCase):
    def test_empty_gets_rgb_default(self):
        out = ensure_band_tile_params({})
        self.assertEqual(out["scheme"], "band")
        self.assertEqual(
            out["band_visualization_params"], DEFAULT_RGB_BAND_VISUALIZATION_PARAMS
        )

    def test_preserves_extras_drops_colormap_keys(self):
        out = ensure_band_tile_params(
            {
                "scheme": "discrete",
                "values": [1, 2],
                "palette": ["#ff0000", "#00ff00"],
                "rescale": "0,255",
            }
        )
        self.assertEqual(out["scheme"], "band")
        self.assertEqual(
            out["band_visualization_params"], DEFAULT_RGB_BAND_VISUALIZATION_PARAMS
        )
        self.assertEqual(out["rescale"], "0,255")
        self.assertNotIn("palette", out)
        self.assertNotIn("values", out)

    def test_keeps_custom_band_visualization_params(self):
        custom = "bidx=4&bidx=3&bidx=2"
        out = ensure_band_tile_params(
            {"scheme": "band", "band_visualization_params": custom}
        )
        self.assertEqual(out["band_visualization_params"], custom)


# ---------------------------------------------------------------------------
# Raster style (pure helpers; no DB)
# ---------------------------------------------------------------------------


class NormalizeTileParamsTests(unittest.TestCase):
    def test_discrete_descrete_alias(self):
        out = normalize_tile_params(
            {
                "scheme": "descrete",
                "max": 2,
                "palette": ["#aabbcc", "#112233"],
            }
        )
        self.assertEqual(out["scheme"], "discrete")
        self.assertEqual(out["palette"], ["#aabbcc", "#112233"])

    def test_discrete_with_explicit_values(self):
        out = normalize_tile_params(
            {
                "scheme": "discrete",
                "values": [1, 2, 5],
                "palette": ["#ff0000", "#00ff00", "#0000ff"],
            }
        )
        self.assertEqual(out["values"], [1.0, 2.0, 5.0])


class BuildColormapForTitilerTests(unittest.TestCase):
    def test_discrete_arbitrary_values(self):
        s = build_colormap_for_titiler(
            {
                "scheme": "discrete",
                "min": 1,
                "max": 5,
                "values": [1, 2, 3, 4, 5],
                "palette": [
                    "#7c3d04",
                    "#c29c6c",
                    "#ffffff",
                    "#34d339",
                    "#006414",
                ],
            }
        )
        self.assertIsInstance(s, str)
        data = json.loads(s)
        self.assertEqual(len(data), 5)
        self.assertEqual(data["1"], [124, 61, 4])
        self.assertEqual(data["5"], [0, 100, 20])

    def test_discrete_normalized_float_values_use_int_keys(self):
        s = build_colormap_for_titiler(
            normalize_tile_params(
                {
                    "scheme": "discrete",
                    "values": [10, 20],
                    "palette": ["#ff0000", "#00ff00"],
                }
            )
        )
        data = json.loads(s)
        self.assertIn("10", data)
        self.assertNotIn("10.0", data)

    def test_extras_only_returns_empty_colormap(self):
        s = build_colormap_for_titiler({"rescale": "0,100", "bidx": 1})
        self.assertEqual(s, "")

    def test_linear_intervals(self):
        s = build_colormap_for_titiler(
            {
                "scheme": "linear",
                "min": 0,
                "values": [10, 20, 30],
                "palette": ["#000000", "#808080", "#ffffff"],
            }
        )
        data = json.loads(s)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)


class ParseQmlSldTests(unittest.TestCase):
    def test_parse_sld(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld" version="1.0.0">
          <sld:UserStyle>
            <sld:FeatureTypeStyle>
              <sld:Rule>
                <sld:RasterSymbolizer>
                  <sld:ColorMap>
                    <sld:ColorMapEntry color="#ff0000" quantity="1" />
                    <sld:ColorMapEntry color="#00ff00" quantity="2" />
                    <sld:ColorMapEntry color="#0000ff" quantity="3" />
                  </sld:ColorMap>
                </sld:RasterSymbolizer>
              </sld:Rule>
            </sld:FeatureTypeStyle>
          </sld:UserStyle>
        </sld:StyledLayerDescriptor>"""
        d = parse_sld_raster_colormap(xml)
        self.assertEqual(d["scheme"], "discrete")
        self.assertEqual(d["values"], [1.0, 2.0, 3.0])
        self.assertEqual(d["palette"], ["#ff0000", "#00ff00", "#0000ff"])

    def test_parse_qml_pseudocolor(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <qgis version="3.0" stylecategories="AllStyleCategories">
          <pipe>
            <rasterrenderer type="singlebandpseudocolor" band="1" classificationMax="3" classificationMin="1">
              <rasterTransparency/>
              <minValue>1</minValue>
              <maxValue>3</maxValue>
              <rastershader>
                <colorrampshader colorRampType="INTERPOLATED" minimumValue="1" maximumValue="3" classificationMode="1">
                  <item alpha="255" value="1" label="1" color="#ff0000"/>
                  <item alpha="255" value="2" label="2" color="#00ff00"/>
                  <item alpha="255" value="3" label="3" color="#0000ff"/>
                </colorrampshader>
              </rastershader>
            </rasterrenderer>
          </pipe>
        </qgis>"""
        d = parse_qml_raster_pseudocolor(xml)
        self.assertEqual(d["scheme"], "discrete")
        self.assertEqual(len(d["values"]), 3)


class TitilerComposeTests(unittest.TestCase):
    def test_compose_uses_colormap_param(self):
        params = compose_titiler_tilejson_params(
            "http://minio/bucket/cog.tif",
            "WorldCRS84Quad",
            color_map_json='{"1": [255,0,0]}',
            extra_params={},
        )
        self.assertIn(("colormap", '{"1": [255,0,0]}'), params)

    def test_compose_preserves_multiple_bidx_for_rgb(self):
        params = compose_titiler_tilejson_params(
            "http://minio/bucket/cog.tif",
            "WorldCRS84Quad",
            band_visualization_params="bidx=1&bidx=2&bidx=3",
            extra_params={"tilesize": "512"},
        )
        bidx_vals = [v for k, v in params if k == "bidx"]
        self.assertEqual(bidx_vals, ["1", "2", "3"])
        self.assertIn(("tilesize", "512"), params)

    def test_compose_skips_extra_bidx_when_band_fragment_set(self):
        params = compose_titiler_tilejson_params(
            "http://minio/bucket/cog.tif",
            "WorldCRS84Quad",
            band_visualization_params="bidx=1&bidx=2&bidx=3",
            extra_params={"bidx": "9", "tilesize": "512"},
        )
        bidx_vals = [v for k, v in params if k == "bidx"]
        self.assertEqual(bidx_vals, ["1", "2", "3"])
