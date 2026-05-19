import logging
import os
from collections.abc import Mapping
import requests

from catalog.style.normalize import split_tile_params
from catalog.style.titiler_export import (
    build_colormap_for_titiler,
    compose_titiler_tilejson_params,
    titiler_extra_query_params,
)

stac_api_url = os.getenv("STAC_API_URL", "http://stac_api:8080")
titiler_url = os.getenv("TITILER_URL", "http://titiler")
minio_endpoint = os.getenv("MINIO_ENDPOINT_PUBLIC", "http://minio:9000")
tile_matrix_id = os.getenv("TileMatrixSetId", default="WorldCRS84Quad")
https_end_point_url = os.getenv("HTTPS_ENDPOINT_URL")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class DatasetVisualization:

    def __init__(self, date, dataset_id, cadence):
        self.date = date
        self.dataset_id = dataset_id
        self.cadence = cadence
        self.stack_items = None
        self.stack_item_url = None
        self.http_url = None
        self.legend_dict = None

    def _parse_date(self):
        """Parse date string into year, month, day components."""
        parts = self.date.split("-")
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2]) if len(parts) == 3 else None
        return year, month, day

    def _get_month_range(self, year, month):
        """Get datetime range for entire month."""
        start = f"{year:04d}-{month:02d}-01T00:00:00Z"
        next_month = 1 if month == 12 else month + 1
        next_year = year + 1 if month == 12 else year
        end = f"{next_year:04d}-{next_month:02d}-01T00:00:00Z"
        return start, end

    def _get_day_range(self, year, month, day):
        """Get datetime range for specific day."""
        start = f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z"
        end = f"{year:04d}-{month:02d}-{day:02d}T23:59:59Z"
        return start, end

    def _handle_monthly(self, year, month, day):
        """Handle monthly cadence: always return full month."""
        return self._get_month_range(year, month)

    def _handle_dekadal(self, year, month, day):
        """Handle dekadal cadence: full month if no day, specific dekad if day given."""
        if day is None:
            return self._get_month_range(year, month)
        return self._get_day_range(year, month, day)

    def _handle_daily(self, year, month, day):
        """Handle daily cadence: specific day only."""
        if day is None:
            raise ValueError("Daily cadence requires full date (YYYY-MM-DD)")
        return self._get_day_range(year, month, day)

    def _query_stac(self, start, end):
        """Query STAC API with datetime range."""
        url = f"{stac_api_url}/collections/{self.dataset_id}/items"
        log.info(f"Querying STAC API at {url} with datetime range {start} to {end}")
        params = {"datetime": f"{start}/{end}", "limit": 100}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        return response.json().get("features", [])

    def get_dataset_items(self):
        """
        Get STAC items for the dataset based on date and cadence.
        Defaults to full month query if cadence is invalid.

        Returns:
            List of STAC items with metadata and asset URLs
        """
        year, month, day = self._parse_date()

        cadence_handlers = {
            "monthly": self._handle_monthly,
            "dekadal": self._handle_dekadal,
            "daily": self._handle_daily,
        }

        handler = cadence_handlers.get(self.cadence, self._handle_monthly)

        start, end = handler(year, month, day)
        self.stack_items = self._query_stac(start, end)
        return self.stack_items

    def get_tile_params_for_dataset(self):
        """
        Return tile params for layers tied to this dataset_id (first matching layer).

        Returns:
            dict or None: Tile params JSON for visualization.
        """
        from catalog.models import DatasetPage

        try:
            dataset_page = DatasetPage.objects.select_related("style_config").get(
                dataset_id=self.dataset_id
            )
        except DatasetPage.DoesNotExist:
            self.legend_dict = None
            return None

        style = getattr(dataset_page, "style_config", None)
        if not style:
            self.legend_dict = None
            return None

        self.legend_dict = style.legend or None
        return style.tile_params or None

    def get_s3_url(self):
        """for now just get the first item in the stack"""
        if self.stack_items is not None:
            self.stack_item_url = self.stack_items[0]["assets"]["data"]

        return self.stack_item_url

    def s3_to_http_url(self):

        s3_stack_item = self.get_s3_url()
        if not s3_stack_item:
            self.http_url = None
            return None
        s3_url = s3_stack_item["href"]
        path = s3_url.replace("s3://", "")
        self.http_url = f"{minio_endpoint}/{path}"
        return self.http_url

    def get_titiler_url(
        self,
        color_map_json="",
        replace_url=False,
        band_visualization_params=None,
        extra_params=None,
    ):
        """
        Request TileJSON from TiTiler. Uses the ``colormap`` query parameter (TiTiler / rio-tiler).
        ``band_visualization_params`` is a raw query fragment merged into the request.
        """
        try:
            base = f"{titiler_url}/cog/WebMercatorQuad/tilejson.json"
            params = compose_titiler_tilejson_params(
                self.http_url,
                tile_matrix_id,
                color_map_json=color_map_json or "",
                band_visualization_params=band_visualization_params,
                extra_params=extra_params,
            )

            param_keys = [k for k, _ in params]
            log.info("Requesting TiTiler URL: %s with params keys %s", base, param_keys)
            log.info(f"Params: {params}")
            tiled_output = requests.get(base, params=params, timeout=30)
            if tiled_output.status_code == 200:
                log.info("TiTiler request successful")
                tiled_output_json = tiled_output.json()

                if replace_url:
                    log.info(
                        "Replacing URLs in TiTiler response with custom endpoint %s",
                        tiled_output_json.get("tiles"),
                    )
                    tiled_output_json["tiles"] = [
                        self.replace_url_with_titiler(url) for url in tiled_output_json["tiles"]
                    ]
                return tiled_output_json
            log.error(
                "TiTiler request failed with status code %s: %s",
                tiled_output.status_code,
                tiled_output.text,
            )

        except Exception as e:
            log.error(f"Error creating titiler URL: {e}")
            return None

    def replace_url_with_titiler(self, url, replaced_str=https_end_point_url):
        """
        Replace the hardcoded base URL with the desired TiTiler endpoint
        """
        if not replaced_str:
            return url
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        if "/titiler" in url:
            return url

        titiler_endpoint = f"{replaced_str}/titiler"
        return url.replace(replaced_str, titiler_endpoint)

    def get_visualization(self, replace_url=False):
        """
        Get visualization parameters for the dataset, including tile URL and color map.
        Returns:
            dict: TileJSON from TiTiler or None.
        """
        try:
            self.get_dataset_items()
            self.s3_to_http_url()
            style_parameters = self.get_tile_params_for_dataset()

            log.info(f"Style parameters for dataset {self.dataset_id} gotten")

            extra_flat = {}
            if style_parameters:
                _, extras = split_tile_params(style_parameters)
                extra_flat = titiler_extra_query_params(extras)
                cmap_result = build_colormap_for_titiler(style_parameters)
            else:
                cmap_result = ""

            if isinstance(cmap_result, Mapping):
                log.info(f"dataset {self.dataset_id} has band visualization parameters")
                titiler_result = self.get_titiler_url(
                    color_map_json="",
                    replace_url=replace_url,
                    band_visualization_params=cmap_result["band_visualization_params"],
                    extra_params=extra_flat,
                )
            else:
                titiler_result = self.get_titiler_url(
                    color_map_json=cmap_result or "",
                    replace_url=replace_url,
                    extra_params=extra_flat,
                )

            log.info(f"Tile params for dataset {self.dataset_id}: fetched")

            return titiler_result
        except Exception as e:
            log.error(f"Error getting visualization for dataset {self.dataset_id}: {e}")
            return None

    def get_stac_tile_url(self):
        try:
            stac_item = self.stack_items[0]
            item_id = stac_item["id"]
            stac_item_url = f"{stac_api_url}/collections/{self.dataset_id}/items/{item_id}"
            tile_url = f"{titiler_url}/stac/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}?url={stac_item_url}&tile_format=png&tileMatrixSetId={tile_matrix_id}&assets=data"
            return tile_url
        except Exception as e:
            log.error(f"Error occured generation stac tile URL: {e}")
            return None


if __name__ == "__main__":
    viz = DatasetVisualization("2025-12", "trees", "monthly")
    items = viz.get_dataset_items()
    http_url = viz.s3_to_http_url()
    titiler = viz.get_titiler_url()
