from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

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

_VALID_AGG = {"raw", "hourly", "daily", "monthly"}


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

    Query parameters
    ----------------
    variable  : str   Required. One of: temp, dewpoint, rh, pressure,
                      wind_speed, wind_direction, rainfall, visibility,
                      elevation, solar_radiation
    agg       : str   Aggregation level: raw | hourly | daily (default) | monthly
    start     : str   Start date (ISO 8601). Default: 30 days ago.
    end       : str   End date (ISO 8601). Default: today.

    Response shape
    --------------
    Aggregated (hourly/daily/monthly):
        {station_code, station_name, variable, aggregation, start, end,
         data: [{period, avg, min, max, count}, ...]}

    Raw:
        {station_code, station_name, variable, aggregation, start, end,
         data: [{period, value, unit}, ...]}
        Raw mode is capped at 5000 rows.
    """

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
