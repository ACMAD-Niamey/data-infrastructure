from collections import OrderedDict
from datetime import date
from django.db import connections
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
import os
import logging
import requests as http_requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

from .serializers import (
    DatasetAvailabilityResponseSerializer,
    DatasetVisualizationRequestSerializer,
    DatasetVisualizationResponseSerializer
)

from .utils import DatasetVisualization

replace_titiler_url = os.getenv("REPLACE_TITILER_URL", "false").lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# GeoServer proxy helpers
# ---------------------------------------------------------------------------

def _fetch_geoserver_availability(layer) -> dict:
    """Fetch and normalise availability from an external GeoServer availability API."""
    try:
        resp = http_requests.get(
            layer.availability_api_url,
            params={"data_name": layer.data_name},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get(layer.data_name, {})
    except Exception as exc:
        log.warning("GeoServer availability fetch failed for %s: %s", layer.dataset_id, exc)
        return {"dataset_id": layer.dataset_id, "cadence": layer.cadence,
                "available": [], "min": None, "max": None}

    dates = []
    for year, year_data in data.items():
        if not str(year).isdigit():
            continue
        months = year_data.get("months", [])
        dekads = year_data.get("dekads", [])
        if layer.cadence == "dekadal":
            for month in months:
                for dekad in dekads:
                    dates.append(f"{year}-{month}-{dekad.zfill(2)}")
        elif layer.cadence == "monthly":
            for month in months:
                dates.append(f"{year}-{month}")
        else:  # daily — treat months as approximate; availability API doesn't give daily
            for month in months:
                dates.append(f"{year}-{month}-01")

    dates.sort(reverse=True)
    return {
        "dataset_id": layer.dataset_id,
        "cadence": layer.cadence,
        "available": dates,
        "max": dates[0] if dates else None,
        "min": dates[-1] if dates else None,
    }


def _build_geoserver_tile_url(layer, date_str: str) -> str:
    """Fill the WMS URL template with the chosen date."""
    parts = date_str.split("-")
    year  = parts[0]
    month = parts[1] if len(parts) > 1 else "01"
    day   = parts[2].zfill(2) if len(parts) > 2 else "01"
    url = layer.wms_url_template
    url = url.replace("{year}", year).replace("{MM}", month).replace("{DD}", day)
    if layer.timescale:
        url = url.replace("{TS}", layer.timescale)
    return url

def to_dekad_start(d: date) -> date:
    # 1–10 => 1st, 11–20 => 11th, 21+ => 21st
    if d.day <= 10:
        return d.replace(day=1)
    if d.day <= 20:
        return d.replace(day=11)
    return d.replace(day=21)

class DatasetAvailabilityView(APIView):
    """
    Get available dates for a dataset from pgSTAC.
    Returns dates aggregated by the specified cadence (daily, dekadal, or monthly).
    """
    # reuse your API key auth, same as ingest
    # permission_classes = [HasAPIKey]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="cadence",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Temporal cadence to aggregate availability (daily, dekadal, or monthly)",
                enum=["daily", "dekadal", "monthly"],
                default="daily",
            ),
        ],
        responses={200: DatasetAvailabilityResponseSerializer},
        tags=["catalog"],
        summary="Get dataset availability",
        description="Returns available dates for a dataset from pgSTAC, aggregated by cadence. "
                    "Daily returns individual dates, dekadal returns 10-day periods, "
                    "monthly returns year-month strings.",
    )
    def get(self, request, dataset_id: str):
        from catalog.models import GeoServerLayer, StaticWmsLayer

        # Static WMS layers have no date dimension — return the layer's last update date as a stable single entry
        sw_layer = StaticWmsLayer.objects.filter(dataset_id=dataset_id).first()
        if sw_layer:
            updated = sw_layer.updated_at.date().isoformat()
            return Response({
                "dataset_id": dataset_id,
                "cadence": "static",
                "available": [updated],
                "max": updated,
                "min": updated,
            }, status=status.HTTP_200_OK)

        # Route to GeoServer proxy if this dataset_id belongs to a GeoServerLayer
        gs_layer = GeoServerLayer.objects.filter(dataset_id=dataset_id).first()
        if gs_layer:
            return Response(_fetch_geoserver_availability(gs_layer), status=status.HTTP_200_OK)

        cadence = (request.query_params.get("cadence") or "daily").lower()
        # If you have cadence in Wagtail, you can fetch it here instead.
        # For now, allow cadence in querystring or default daily.
        if cadence not in ("daily", "dekadal", "monthly", ""):
            return Response({"detail": "cadence must be daily|dekadal|monthly"}, status=400)
        if cadence == "":
            cadence = "daily"

        # Fetch distinct UTC dates from pgSTAC
        sql_dates = """
            SELECT DISTINCT (datetime AT TIME ZONE 'UTC')::date AS d
            FROM pgstac.items
            WHERE collection = %s
            ORDER BY d;
        """
        sql_minmax = """
            SELECT
              MIN((datetime AT TIME ZONE 'UTC')::date) AS min_d,
              MAX((datetime AT TIME ZONE 'UTC')::date) AS max_d
            FROM pgstac.items
            WHERE collection = %s;
        """

        with connections["pgstac"].cursor() as cur:
            cur.execute(sql_minmax, [dataset_id])
            min_d, max_d = cur.fetchone()

            cur.execute(sql_dates, [dataset_id])
            rows = [r[0] for r in cur.fetchall()]  # list[date]

        if not rows:
            return Response(
                {"dataset_id": dataset_id, "cadence": cadence, "available": [], "min": None, "max": None},
                status=status.HTTP_200_OK,
            )

        if cadence == "daily":
            available = [d.isoformat() for d in rows]

        elif cadence == "dekadal":
            seen = OrderedDict()
            for d in rows:
                k = to_dekad_start(d).isoformat()
                seen[k] = True
            available = list(seen.keys())

        else:  # monthly
            seen = OrderedDict()
            for d in rows:
                k = f"{d.year:04d}-{d.month:02d}"
                seen[k] = True
            available = list(seen.keys())

        return Response(
            {
                "dataset_id": dataset_id,
                "cadence": cadence,
                "available": available,
                "min": min_d.isoformat() if min_d else None,
                "max": max_d.isoformat() if max_d else None,
            },
            status=status.HTTP_200_OK,
        )

class DatasetVisualizationView(APIView):
    """
    Get visualization parameters for a dataset.
    Returns a URL to a titiler endpoint that can be used to visualize the dataset on the frontend.
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Specific date to visualize (YYYY-MM or YYYY-MM-DD)",
                required=True,
            ),
            OpenApiParameter(
                name="cadence",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Temporal cadence for visualization",
                enum=["daily", "dekadal", "monthly"],
                required=True,
            ),
        ],
        responses={200: DatasetVisualizationResponseSerializer},
        tags=["catalog"],
        summary="Get dataset visualization parameters",
        description="Returns a json containing a URL to a titiler endpoint for visualizing the dataset on the frontend. "
                    "The titiler URL is generated based on the dataset and date, and can be used to display "
                    "the dataset as a map layer in the UI.",
    )
    def get(self, request, dataset_id: str):
        from catalog.models import GeoServerLayer, StaticWmsLayer

        # Static WMS layers — return the tile URL directly, date is ignored
        sw_layer = StaticWmsLayer.objects.filter(dataset_id=dataset_id).first()
        if sw_layer:
            return Response(
                {
                    "dataset_id": dataset_id,
                    "cadence": "static",
                    "titiler_url": [sw_layer.tile_url],
                    "titiler_info": {"tiles": [sw_layer.tile_url], "bounds": None},
                },
                status=status.HTTP_200_OK,
            )

        # Route to GeoServer proxy if this dataset_id belongs to a GeoServerLayer
        gs_layer = GeoServerLayer.objects.filter(dataset_id=dataset_id).first()
        if gs_layer:
            date_param = request.query_params.get("date", "")
            if not date_param:
                return Response({"detail": "date is required"}, status=400)
            tile_url = _build_geoserver_tile_url(gs_layer, date_param)
            return Response(
                {
                    "dataset_id": dataset_id,
                    "cadence": gs_layer.cadence,
                    "titiler_url": [tile_url],
                    "titiler_info": {"tiles": [tile_url], "bounds": None},
                },
                status=status.HTTP_200_OK,
            )

        serializer = DatasetVisualizationRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        date = serializer.validated_data["date"]
        cadence = serializer.validated_data["cadence"]

        try:
            visualization_info = DatasetVisualization(date, dataset_id, cadence)
            log.info(f'replace_titiler_url={replace_titiler_url}')
            titiler_info = visualization_info.get_visualization(replace_url=replace_titiler_url)

            if not titiler_info:
                return Response({"detail": "No visualization available for this dataset/date"}, status=404)
            titiler_url = titiler_info.get("tiles")

            return Response(
                {
                    "dataset_id": dataset_id,
                    "cadence": visualization_info.cadence,
                    "titiler_url": titiler_url if titiler_url else None,
                    "titiler_info": titiler_info,
                    "legend": visualization_info.legend_dict,
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)


  