"""Bridge from a downloaded THREDDS CSV to a GeoTIFF, via utils.raster_converstions.

Some THREDDS products (e.g. the Meningitis Vigilance GEFS series) publish
lon/lat/value CSVs instead of rasters. The downstream ingest pipeline
(ingest.cog.ensure_raster_is_cog) only COG-optimizes .tif/.tiff keys, so a
CSV needs converting before it's uploaded - this module is that step, kept
separate from workflow_runner so the conversion itself stays independently
testable.
"""

from __future__ import annotations

from pathlib import Path

from utils.raster_converstions import csv_to_raster

from ..models import DownloadWorkflowFile


def convert_to_raster(csv_path: Path, workflow_file: DownloadWorkflowFile, output_dir: Path) -> Path:
    if not workflow_file.csv_value_column:
        raise ValueError(
            f"{workflow_file} downloaded a CSV ({csv_path.name}) but has no csv_value_column configured"
        )
    tif_path = csv_to_raster(
        csv_path=str(csv_path),
        column=workflow_file.csv_value_column,
        path=str(output_dir),
    )
    return Path(tif_path)
