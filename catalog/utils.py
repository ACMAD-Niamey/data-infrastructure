import http
import requests
import os 
import logging
import json

from catalog.models import Layer

stac_api_url = os.getenv("STAC_API_URL", "http://stac_api:8080")
titiler_url = os.getenv("TITILER_URL", "http://titiler")
minio_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
tile_matrix_id = os.getenv("TileMatrixSetId", default="WorldCRS84Quad")
https_end_point_url = os.getenv("HTTPS_ENDPOINT_URL")    

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class DatasetVisualization:

    def __init__(self, date, dataset_id, cadence):
        self.date = date
        self.dataset_id = dataset_id
        self.cadence = cadence
        self.stack_items =None 
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
        params = {"datetime": f"{start}/{end}", "limit": 100}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json().get("features", [])
    
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
        
        # Default to full month if cadence not found
        handler = cadence_handlers.get(self.cadence, self._handle_monthly)
        
        start, end = handler(year, month, day)
        self.stack_items = self._query_stac(start, end)
        return self.stack_items

    def get_tile_params_for_dataset(self):
        """
        Return tile params for all layers tied to this dataset_id.

        Returns:
            list: Tile params objects (JSON) for each layer.
        """
        dataset_info = Layer.objects.filter(dataset__dataset_id=self.dataset_id).values("tile_params", "legend").first()

        self.legend_dict = dataset_info["legend"] if dataset_info else None

        return dataset_info["tile_params"] if dataset_info else None
    
    def get_s3_url(self):
        """for now just get the first item in the stack """
        if self.stack_items is not None:
            self.stack_item_url = self.stack_items[0]['assets']['data']
        
        return self.stack_item_url

    
    def s3_to_http_url(self):
        
        s3_stack_item = self.get_s3_url()
        if s3_stack_item:
            s3_url = s3_stack_item["href"]
            path = s3_url.replace("s3://", "")
            self.http_url = f"{minio_endpoint}/{path}"
        return f"{minio_endpoint}/{path}"
    
    def get_titiler_url(self, color_map={}, replace_url=True):
        try:
            titiler_request_url = f"{titiler_url}/cog/WebMercatorQuad/tilejson.json?url={self.http_url}&tile_format=png&tileMatrixSetId={tile_matrix_id}&colormap={color_map}"
            log.info(f"Requesting TiTiler URL: {titiler_request_url}")
            tiled_output = requests.get(titiler_request_url) 
            if tiled_output.status_code == 200:
                log.info(f"TiTiler request successful:")
                if replace_url:
                    tiled_output['tiles'] = [self.replace_url_with_titiler(url) for url in tiled_output.get('tiles', [])] if replace_url else tiled_output
                return tiled_output
            else:
                log.error(f"TiTiler request failed with status code {tiled_output.status_code}: {tiled_output.text}")
            
        except Exception as e:
            log.error(f"Error creating titiler URL: {e}")
            return None
        
    
    def replace_url_with_titiler(self, url, replaced_str=https_end_point_url):
        """
        Replace the hardcoded base URL with the desired TiTiler endpoint
        """
        # Ensure it's https
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        # Avoid double "titiler"
        if "/titiler" in url:
            return url

        titiler_endpoint = f"{replaced_str}/titiler"
        return url.replace(replaced_str, titiler_endpoint)
    
    def hex_to_rgb(self,hex):
        """
        Convert hex color to RGB tuple.
        Args:
            hex (str): Hex color code (e.g., "#FFFFFF").
        Returns:
            list of integers:  [R, G, B].
        """
        hex = hex.lstrip("#")
        return [int(hex[i:i+2], 16) for i in (0, 2, 4)]


    def get_visualization(self):
        """
        Get visualization parameters for the dataset, including tile URL and color map.
        Returns:
            dict: Visualization parameters including 'tile_url' and 'color_map'.
        """
        self.get_dataset_items()
        self.s3_to_http_url()
        style_parameters = self.get_tile_params_for_dataset()

        log.info(f"Style parameters for dataset {self.dataset_id} goten ")
        
        cmap = self.get_color_map_titiler(style_parameters) if style_parameters else {}
        log.info(f"Tile params for dataset {self.dataset_id}: {cmap}")
        titiler_url = self.get_titiler_url(color_map=cmap if cmap else {})

        return titiler_url
     

    def get_stac_tile_url(self):
        try:
            stac_item = self.stack_items[0]
            item_id = stac_item['id']
            stac_item_url = f"{stac_api_url}/collections/{self.dataset_id}/items/{item_id}"
            tile_url = f"{titiler_url}/stac/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}?url={stac_item_url}&tile_format=png&tileMatrixSetId={tile_matrix_id}&assets=data"
            return tile_url
        except Exception as e:
            log.error(f"Error occured generation stac tile URL: {e}")
            return None
        
    def get_style_map_parameters(self):
       pass 

    def get_color_map_descrete(self,style):
        """
        Create a color map for discrete values.
        Args:
            style (dict): Style dictionary containing 'palette' and 'max' keys.
        Returns:
            str: JSON string of color map of rgb colors.
        """
        color_map = dict()
        max_value = int(style.get('max'))
        for i in range(max_value):
            color_map[i+1] = self.hex_to_rgb(style['palette'][i])
        return json.dumps(color_map)
    
    def get_color_map_linear(self, style:dict):
        color_map = []
        min_value = int(style.get('min', 0))
        color_map.append(([min_value , style['values'][0]], self.hex_to_rgb(style['palette'][0])))

        values = style.get('values')

        # Loop over values to create ranges
        for i in range(len(values) - 1):
            val_range = [values[i], values[i + 1]]
            rgba = self.hex_to_rgb(style["palette"][i + 1])
            color_map.append((val_range, rgba))

        return json.dumps(color_map)
    
    def get_color_map_titiler(self,style):

        scheme = style.get("scheme")
        if scheme == 'linear':
            # check if values exists 
            if style.get('values') is not None:
                color_map = self.get_color_map_linear(style)
            else:
                raise ValueError("Values are required for linear scheme")
        elif scheme == 'descrete':
            color_map = self.get_color_map_descrete(style)
        else:
            raise ValueError(f"Unknown scheme: {scheme}")
        return color_map


if __name__ == "__main__":
    viz = DatasetVisualization("2025-12", "trees", "monthly")
    items = viz.get_dataset_items()
    http_url = viz.s3_to_http_url()
    titiler =viz.get_titiler_url()

