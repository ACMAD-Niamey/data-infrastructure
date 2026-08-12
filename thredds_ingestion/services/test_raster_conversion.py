import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import rasterio
from django.test import SimpleTestCase

from .raster_conversion import convert_to_raster

CSV_CONTENT = """Data$x,y,Vigilance
-0.5,10,4
0.0,10,3
-0.5,10.5,2
0.0,10.5,4
"""


def _workflow_file(csv_value_column="Vigilance"):
    wff = MagicMock()
    wff.csv_value_column = csv_value_column
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

    def test_missing_csv_value_column_raises_clear_error(self):
        with self.assertRaises(ValueError):
            convert_to_raster(self.csv_path, _workflow_file(csv_value_column=""), Path(self.tmp_dir.name))
