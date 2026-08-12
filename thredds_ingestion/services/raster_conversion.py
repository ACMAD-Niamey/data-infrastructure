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

from catalog.models import DatasetPage
from catalog.ui_layers import dataset_description_payload
from utils.raster_converstions import csv_to_raster

from ..models import DownloadWorkflowFile


def _dataset_metadata(dataset: DatasetPage) -> dict[str, str]:
    """GeoTIFF tags carrying dataset context onto the generated raster -
    reuses the same plain-text description already computed for the
    catalog UI (catalog.ui_layers), rather than re-stripping rich text here.
    """
    metadata = {"dataset_id": dataset.dataset_id, "title": dataset.title, "cadence": dataset.cadence}
    description = dataset_description_payload(dataset)["plain"]
    if description:
        metadata["description"] = description
    return metadata


def convert_to_raster(csv_path: Path, workflow_file: DownloadWorkflowFile, output_dir: Path) -> Path:
    if not workflow_file.csv_value_column:
        raise ValueError(
            f"{workflow_file} downloaded a CSV ({csv_path.name}) but has no csv_value_column configured"
        )

    # Only override the util's own resolution defaults when the workflow_file
    # explicitly configures one - leave csv_to_raster's kwarg defaults (0.5°)
    # in charge otherwise, rather than re-declaring them here.
    resolution_kwargs = {}
    if workflow_file.csv_x_res is not None:
        resolution_kwargs["x_res"] = workflow_file.csv_x_res
    if workflow_file.csv_y_res is not None:
        resolution_kwargs["y_res"] = workflow_file.csv_y_res

    tif_path = csv_to_raster(
        csv_path=str(csv_path),
        column=workflow_file.csv_value_column,
        path=str(output_dir),
        metadata=_dataset_metadata(workflow_file.dataset),
        **resolution_kwargs,
    )
    return Path(tif_path)
