
import os
import pandas as pd
import rasterio
from rasterio.transform import Affine
import numpy as np
import logging



log = logging.getLogger(__name__)

def csv_to_raster(
    csv_path: str,
    column: str,
    x_res: float = 0.5,
    y_res: float = 0.5,
    metadata: dict | None = None,
    path: str = "data/rasters",
    xy_columns: tuple[str, str] = ("Data$x", "y"),
) -> str:
    """
    Convert a CSV containing longitude, latitude and value columns
    to a GeoTIFF raster.

    Args:
        csv_path: Path to source CSV.
        column: Column containing raster values.
        x_res: Longitude resolution in degrees.
        y_res: Latitude resolution in degrees.
        metadata: Optional GeoTIFF metadata.
        path: Output directory.
        xy_columns: Tuple/list containing longitude and latitude column names.

    Returns:
        Path to created GeoTIFF.
    """

    log.info("raster creation started")

    data = pd.read_csv(csv_path)

    lon_col = xy_columns[0]
    lat_col = xy_columns[1]

    # Get spatial extent from the CSV.
    min_lon = data[lon_col].min()
    max_lon = data[lon_col].max()
    min_lat = data[lat_col].min()
    max_lat = data[lat_col].max()

    # Coordinates in this dataset represent grid-cell centres,
    # so extend the bounds by half a pixel.
    west = min_lon - (x_res / 2)
    east = max_lon + (x_res / 2)
    south = min_lat - (y_res / 2)
    north = max_lat + (y_res / 2)

    width = int(round((east - west) / x_res))
    height = int(round((north - south) / y_res))

    nodata = -9999

    # Float32 is safer for general weather/climate variables.
    raster = np.full(
        (height, width),
        nodata,
        dtype=np.float32
    )

    for _, row in data.iterrows():

        lon = row[lon_col]
        lat = row[lat_col]

        # Convert longitude/latitude to pixel position.
        col = int(round((lon - min_lon) / x_res))

        # Raster rows start from NORTH and increase southward.
        raster_row = int(round((max_lat - lat) / y_res))

        raster[raster_row, col] = row[column]

    # Upper-left origin.
    transform = Affine.translation(
        west,
        north
    ) * Affine.scale(
        x_res,
        -y_res
    )

    file_name = os.path.basename(csv_path).replace(".csv", ".tif")

    os.makedirs(path, exist_ok=True)

    file_name = os.path.join(path, file_name)

    with rasterio.open(
        file_name,
        mode="w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=nodata,
        compress="lzw",
    ) as dst:

        dst.write(raster, 1)

        if metadata is not None:
            dst.update_tags(**metadata)

    log.info(f"file name: {file_name} created")

    return file_name