from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from observations.services.observation_reader import ObservationReader
from observations.serializers import (
    CountryBoundsOptionSerializer,
    StationFacetsSerializer,
    StationListItemSerializer,
    StationInfoSerializer,
    StationListResponseSerializer,
    StationStatsResponseSerializer,
    TimeSeriesRawBucketSerializer,
    TimeSeriesAggBucketSerializer,
)

log = logging.getLogger(__name__)

_VALID_AGG = {"raw", "hourly", "daily", "monthly", "yearly"}
_STATION_STATS_CACHE_TTL_SECONDS = 60 * 10
_COUNTRY_BOUNDS_CACHE_TTL_SECONDS = 60 * 60
_COUNTRY_BOUNDS_CACHE_KEY = "country_bounds:v2"


def _default_end() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _default_start() -> str:
    d = datetime.now(tz=timezone.utc) - timedelta(days=30)
    return d.strftime("%Y-%m-%d")


class StationListView(APIView):
    """
    GET /api/stations/

    Returns active stations that have at least one observation.
    Optional query params filter by geography; response includes bounding box for map zoom.
    """

    @extend_schema(
        summary="List all stations",
        description=(
            "Returns active stations that have at least one observation. "
            "Optional filters: country_code (ISO alpha-3), admin1, admin2 (exact match). "
            "Includes spatial extent (west/south/east/north in degrees) when any station matches."
        ),
        parameters=[
            OpenApiParameter(
                name="country_code",
                location=OpenApiParameter.QUERY,
                required=False,
                type=OpenApiTypes.STR,
                description="ISO 3166-1 alpha-3 country code (e.g. DZA).",
            ),
            OpenApiParameter(
                name="admin1",
                location=OpenApiParameter.QUERY,
                required=False,
                type=OpenApiTypes.STR,
                description="First administrative area (exact match).",
            ),
            OpenApiParameter(
                name="admin2",
                location=OpenApiParameter.QUERY,
                required=False,
                type=OpenApiTypes.STR,
                description="Second administrative area (exact match).",
            ),
        ],
        responses={200: StationListResponseSerializer},
        tags=["Stations"],
    )
    def get(self, request):
        reader = ObservationReader()
        country_code = request.query_params.get("country_code")
        admin1 = request.query_params.get("admin1")
        admin2 = request.query_params.get("admin2")
        rows = reader.station_list(
            country_code=country_code,
            admin1=admin1,
            admin2=admin2,
        )
        extent = reader.station_list_spatial_extent(
            country_code=country_code,
            admin1=admin1,
            admin2=admin2,
        )
        serializer = StationListItemSerializer(rows, many=True)
        return Response(
            {
                "count": len(rows),
                "results": serializer.data,
                "extent": extent,
            }
        )


class StationFacetsView(APIView):
    """
    GET /api/stations/facets/

    Distinct country_code, admin1, admin2 values for populating filters.
    """

    @extend_schema(
        summary="Station filter facets",
        description="Distinct country/admin1 values present on stations that have observations.",
        parameters=[
            OpenApiParameter(
                name="country_code",
                location=OpenApiParameter.QUERY,
                required=False,
                type=OpenApiTypes.STR,
                description="Optional ISO alpha-3 code to scope admin1 facet values.",
            ),
        ],
        responses={200: StationFacetsSerializer},
        tags=["Stations"],
    )
    def get(self, request):
        reader = ObservationReader()
        country_code = request.query_params.get("country_code")
        data = reader.station_facets(country_code=country_code)
        return Response(StationFacetsSerializer(instance=data).data)


class CountryBoundsView(APIView):
    """
    GET /api/stations/country-bounds/

    Returns country options from configured ``CountryBoundary`` rows with
    precomputed bounds for map zoom (not filtered by stations or observations).
    """

    @extend_schema(
        summary="Country bounds options",
        description=(
            "All country boundaries that have a non-empty country code and stored "
            "bounds JSON—sorted by country name—for instant country zoom in the UI."
        ),
        responses={200: CountryBoundsOptionSerializer(many=True)},
        tags=["Stations"],
    )
    def get(self, request):
        cached_payload = cache.get(_COUNTRY_BOUNDS_CACHE_KEY)
        if cached_payload is not None:
            return Response(cached_payload)

        reader = ObservationReader()
        data = reader.country_bounds_options()
        payload = CountryBoundsOptionSerializer(data, many=True).data
        cache.set(_COUNTRY_BOUNDS_CACHE_KEY, payload, _COUNTRY_BOUNDS_CACHE_TTL_SECONDS)
        return Response(payload)


class CountryBoundaryGeoJsonView(APIView):
    """
    GET /api/stations/country-boundary/<country_code>/

    Returns the full GeoJSON Feature for a country boundary polygon.
    Used by the MCP zonal statistics tools for accurate TiTiler masking.
    """

    def get(self, request, country_code: str):
        import json
        from stations.models import CountryBoundary

        boundary = CountryBoundary.objects.filter(
            country_code__iexact=country_code.strip()
        ).first()
        if not boundary:
            return Response(
                {"detail": f"Country boundary for '{country_code}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "type":       "Feature",
            "properties": {"country_code": boundary.country_code, "country_name": boundary.country_name},
            "geometry":   json.loads(boundary.geom.geojson),
        })


class StationDetailView(APIView):
    """
    GET /api/stations/<station_code>/

    Returns metadata for a single station identified by its station_code,
    plus per-variable record counts and date ranges.
    """

    @extend_schema(
        summary="Station detail",
        description=(
            "Returns metadata for a single station identified by `station_code`, "
            "plus per-variable record counts and first/last observation timestamps."
        ),
        parameters=[
            OpenApiParameter(
                name="station_code",
                location=OpenApiParameter.PATH,
                description="Station code (e.g. 60390 or WIGOS_0_20000_0_60401).",
                required=True,
                type=OpenApiTypes.STR,
            ),
        ],
        responses={200: StationInfoSerializer, 404: None},
        tags=["Stations"],
    )
    def get(self, request, station_code: str):
        reader = ObservationReader()
        info = reader.station_info(station_code)

        if info is None:
            return Response(
                {"detail": f"Station '{station_code}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        variables = reader.station_variables(station_code)
        info["variables"] = variables

        serializer = StationInfoSerializer(info)
        return Response(serializer.data)


class StationStatsView(APIView):
    """
    GET /api/stations/<station_code>/stats/

    Returns time-series statistics for one variable at a station.
    """

    @extend_schema(
        summary="Station time-series statistics",
        description=(
            "Returns aggregated or raw time-series for a single variable at a station.\n\n"
            "**Aggregation modes** (`agg` parameter):\n"
            "- `raw` — individual observations (capped at 5 000 rows); "
            "data items contain `period`, `value`, `unit`.\n"
            "- `hourly` — hourly avg / min / max / count.\n"
            "- `daily` — daily avg / min / max / count *(default)*.\n"
            "- `monthly` — monthly avg / min / max / count.\n"
            "- `yearly` — yearly avg / min / max / count.\n\n"
            "Pressure values stored in Pa are automatically converted to hPa."
        ),
        parameters=[
            OpenApiParameter(
                name="station_code",
                location=OpenApiParameter.PATH,
                description="Station code (e.g. 60390).",
                required=True,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="variable",
                location=OpenApiParameter.QUERY,
                description=(
                    "Variable to query. Common values: "
                    "`temp`, `dewpoint`, `rh`, `pressure`, `wind_speed`, "
                    "`wind_direction`, `rainfall`, `visibility`, `elevation`."
                ),
                required=True,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="agg",
                location=OpenApiParameter.QUERY,
                description="Aggregation level (default: daily).",
                required=False,
                type=OpenApiTypes.STR,
                enum=["raw", "hourly", "daily", "monthly", "yearly"],
            ),
            OpenApiParameter(
                name="start",
                location=OpenApiParameter.QUERY,
                description=(
                    "Start date inclusive (ISO 8601, e.g. 2026-04-01). "
                    "Default: 30 days ago."
                ),
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="end",
                location=OpenApiParameter.QUERY,
                description=(
                    "End date inclusive (ISO 8601, e.g. 2026-04-27). "
                    "Default: today."
                ),
                required=False,
                type=OpenApiTypes.DATE,
            ),
        ],
        responses={200: StationStatsResponseSerializer, 400: None, 404: None},
        examples=[
            OpenApiExample(
                "Daily temperature — DAR-EL-BEIDA",
                value={
                    "station_code": "60390",
                    "station_name": "DAR-EL-BEIDA",
                    "variable": "temp",
                    "aggregation": "daily",
                    "start": "2026-04-01",
                    "end": "2026-04-27",
                    "data": [
                        {
                            "period": "2026-04-27T00:00:00Z",
                            "avg": 18.1,
                            "min": 14.2,
                            "max": 24.8,
                            "count": 4,
                        }
                    ],
                },
                response_only=True,
            ),
        ],
        tags=["Stations"],
    )
    def get(self, request, station_code: str):
        variable = request.query_params.get("variable", "").strip()
        if not variable:
            return Response(
                {"detail": "Query parameter 'variable' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agg = request.query_params.get("agg", "daily").strip().lower()
        if agg not in _VALID_AGG:
            return Response(
                {"detail": f"Invalid 'agg'. Choose from: {', '.join(sorted(_VALID_AGG))}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start = request.query_params.get("start", _default_start()).strip()
        end = request.query_params.get("end", _default_end()).strip()

        reader = ObservationReader()
        info = reader.station_info(station_code)
        if info is None:
            return Response(
                {"detail": f"Station '{station_code}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        cache_key = ":".join(
            [
                "station_stats",
                station_code.strip(),
                variable,
                agg,
                start,
                end,
            ]
        )
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        data = reader.time_series_by_station_code(
            station_code=station_code,
            variable_code=variable,
            start=start,
            end=end,
            agg=agg,
        )

        if agg == "raw":
            bucket_serializer = TimeSeriesRawBucketSerializer(data, many=True)
        else:
            bucket_serializer = TimeSeriesAggBucketSerializer(data, many=True)

        payload = {
            "station_code": station_code,
            "station_name": info.get("name"),
            "variable": variable,
            "aggregation": agg,
            "start": start,
            "end": end,
            "data": bucket_serializer.data,
        }

        serializer = StationStatsResponseSerializer(payload)
        response_payload = serializer.data
        if response_payload.get("data"):
            cache.set(cache_key, response_payload, _STATION_STATS_CACHE_TTL_SECONDS)
        return Response(response_payload)
