from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from observations.services.observation_reader import ObservationReader
from observations.serializers import (
    StationListItemSerializer,
    StationInfoSerializer,
    StationStatsResponseSerializer,
    TimeSeriesRawBucketSerializer,
    TimeSeriesAggBucketSerializer,
)

log = logging.getLogger(__name__)

_VALID_AGG = {"raw", "hourly", "daily", "monthly", "yearly"}


def _default_end() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _default_start() -> str:
    d = datetime.now(tz=timezone.utc) - timedelta(days=30)
    return d.strftime("%Y-%m-%d")


class StationListView(APIView):
    """
    GET /api/stations/

    Returns all active stations that have at least one observation.
    Each item includes available variable codes and the latest observation time.
    """

    @extend_schema(
        summary="List all stations",
        description=(
            "Returns all active stations that have at least one observation. "
            "Each record includes coordinates, available variable codes, "
            "and the timestamp of the most recent observation."
        ),
        responses={200: StationListItemSerializer(many=True)},
        tags=["Stations"],
    )
    def get(self, request):
        reader = ObservationReader()
        rows = reader.station_list()
        serializer = StationListItemSerializer(rows, many=True)
        return Response({"count": len(rows), "results": serializer.data})


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

        # Verify the station exists
        info = reader.station_info(station_code)
        if info is None:
            return Response(
                {"detail": f"Station '{station_code}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = reader.time_series_by_station_code(
            station_code=station_code,
            variable_code=variable,
            start=start,
            end=end,
            agg=agg,
        )

        # Serialise each bucket according to aggregation type
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
        return Response(serializer.data)
