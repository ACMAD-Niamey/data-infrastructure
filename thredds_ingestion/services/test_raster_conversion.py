import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import rasterio
from django.test import SimpleTestCase

from .raster_conversion import convert_to_raster

CSV_CONTENT = """Data$x,y,Vigilance
-0.5,10,4
0.0,10,3
-0.5,10.5,2
0.0,10.5,4
"""


def _dataset(dataset_id="meningitis-vigilance-gefs", title="Meningitis Vigilance", cadence="daily", description=""):
    ds = MagicMock()
    ds.dataset_id = dataset_id
    ds.title = title
    ds.cadence = cadence
    ds.description = description
    return ds


def _workflow_file(csv_value_column="Vigilance", csv_x_res=None, csv_y_res=None, dataset=None):
    wff = MagicMock()
    wff.csv_value_column = csv_value_column
    wff.csv_x_res = csv_x_res
    wff.csv_y_res = csv_y_res
    wff.dataset = dataset or _dataset()
    return wff


class ConvertToRasterTests(SimpleTestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.csv_path = Path(self.tmp_dir.name) / "Vigilance_Data_GEFS_Week_1.csv"
        self.csv_path.write_text(CSV_CONTENT)

    def test_converts_csv_to_a_readable_geotiff(self):
        tif_path = convert_to_raster(self.csv_path, _workflow_file(), Path(self.tmp_dir.name))

        self.assertTrue(tif_path.exists())
        self.assertEqual(tif_path.suffix, ".tif")
        with rasterio.open(tif_path) as dataset:
            band = dataset.read(1)
            # Raster rows start from the north: top-left cell is the
            # northwest-most point, x=-0.5, y=10.5 -> Vigilance=2.
            self.assertEqual(band[0, 0], 2)
            # x=-0.5, y=10 (one row south) -> Vigilance=4.
            self.assertEqual(band[1, 0], 4)

    def test_geotiff_tags_carry_dataset_context(self):
        dataset = _dataset(
            dataset_id="meningitis-vigilance-gefs",
            title="Meningitis Vigilance",
            cadence="daily",
            description="<p>Weekly meningitis vigilance outlook.</p>",
        )
        tif_path = convert_to_raster(self.csv_path, _workflow_file(dataset=dataset), Path(self.tmp_dir.name))

        with rasterio.open(tif_path) as ds:
            tags = ds.tags()
        self.assertEqual(tags["dataset_id"], "meningitis-vigilance-gefs")
        self.assertEqual(tags["title"], "Meningitis Vigilance")
        self.assertEqual(tags["cadence"], "daily")
        self.assertIn("Weekly meningitis vigilance outlook.", tags["description"])

    def test_missing_csv_value_column_raises_clear_error(self):
        with self.assertRaises(ValueError):
            convert_to_raster(self.csv_path, _workflow_file(csv_value_column=""), Path(self.tmp_dir.name))

    @patch("thredds_ingestion.services.raster_conversion.csv_to_raster")
    def test_no_resolution_override_leaves_util_defaults_in_charge(self, mock_csv_to_raster):
        mock_csv_to_raster.return_value = str(Path(self.tmp_dir.name) / "out.tif")

        convert_to_raster(self.csv_path, _workflow_file(), Path(self.tmp_dir.name))

        kwargs = mock_csv_to_raster.call_args.kwargs
        self.assertNotIn("x_res", kwargs)
        self.assertNotIn("y_res", kwargs)

    @patch("thredds_ingestion.services.raster_conversion.csv_to_raster")
    def test_configured_resolution_is_passed_through(self, mock_csv_to_raster):
        mock_csv_to_raster.return_value = str(Path(self.tmp_dir.name) / "out.tif")

        convert_to_raster(
            self.csv_path,
            _workflow_file(csv_x_res=1.0, csv_y_res=0.25),
            Path(self.tmp_dir.name),
        )

        kwargs = mock_csv_to_raster.call_args.kwargs
        self.assertEqual(kwargs["x_res"], 1.0)
        self.assertEqual(kwargs["y_res"], 0.25)
