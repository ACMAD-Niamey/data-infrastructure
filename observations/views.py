from rest_framework.response import Response
from rest_framework.views import APIView

from observations.serializers import (
    ObservationRecordSerializer,
    ObservationStatsSerializer,
)
from .services.observation_reader import ObservationReader
from .services.observation_stats import ObservationStatsReader


class LatestObservationsAPIView(APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        records = ObservationReader().latest(limit=limit)
        serializer = ObservationRecordSerializer(records, many=True)
        return Response(serializer.data)


class StationObservationsAPIView(APIView):
    def get(self, request, station_id: int):
        limit = int(request.query_params.get("limit", 100))
        records = ObservationReader().by_station(station_id=station_id, limit=limit)
        serializer = ObservationRecordSerializer(records, many=True)
        return Response(serializer.data)


class VariableObservationsAPIView(APIView):
    def get(self, request, variable_code: str):
        limit = int(request.query_params.get("limit", 100))
        records = ObservationReader().by_variable(variable_code=variable_code, limit=limit)
        serializer = ObservationRecordSerializer(records, many=True)
        return Response(serializer.data)


class ObservationStatsAPIView(APIView):
    def get(self, request):
        stats_reader = ObservationStatsReader()
        by_variable_rows = stats_reader.count_by_variable()

        payload = {
            "total_count": stats_reader.total_count(),
            "latest_timestamp": stats_reader.latest_timestamp(),
            "by_variable": [
                {"variable_code": variable_code, "count": count}
                for variable_code, count in by_variable_rows
            ],
        }

        serializer = ObservationStatsSerializer(payload)
        return Response(serializer.data)