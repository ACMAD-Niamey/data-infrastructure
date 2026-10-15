from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import DatasetPage

from .api import KEY_OR_TOKEN_AUTH
from .permissions import HasAPIKey
from .station_timeseries.uploads import queue_station_timeseries_run


class IngestStationTimeseriesView(APIView):
    """Upload logger CSV files into a station time-series dataset.

    Mirrors the CMS upload: files are queued as a Celery run and the response
    carries the run id to poll in the admin (Ingestion runs).
    """

    authentication_classes = KEY_OR_TOKEN_AUTH
    permission_classes = [HasAPIKey]
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=["ingest"],
        description=(
            "Multipart upload. Field `files` (repeatable): logger CSVs named like "
            "`Capteur 002 Soleil.CSV`. Optional `group` and `commune` text fields."
        ),
    )
    def post(self, request, dataset_id: str):
        dataset = DatasetPage.objects.filter(dataset_id=dataset_id).first()
        if not dataset:
            return Response(
                {"detail": f"Unknown dataset_id '{dataset_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if dataset.dataset_type != "station_timeseries":
            return Response(
                {"detail": f"Dataset '{dataset_id}' is not a station_timeseries dataset"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"detail": "No files uploaded (field 'files')"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run = queue_station_timeseries_run(
            dataset,
            files,
            group=request.data.get("group", ""),
            commune=request.data.get("commune", ""),
        )
        return Response({"run_id": run.id, "status": run.status}, status=status.HTTP_202_ACCEPTED)
