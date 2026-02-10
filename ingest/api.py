from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from catalog.models import DatasetPage
from .auth import HeaderAPIKeyAuthentication
from .models import IngestionRun
from .permissions import HasAPIKey

from .tasks import process_ingestion_run




def validate_payload_for_cadence(cadence: str, payload: dict):
    """
    Minimal validation so your infra stays versatile.
    daily/monthly -> require datetime
    dekadal/seasonal -> require start_datetime and end_datetime
    """
    if cadence in ("daily", "monthly"):
        if not payload.get("datetime"):
            return "Missing required field: datetime"
    elif cadence in ("dekadal", "seasonal"):
        if not payload.get("start_datetime") or not payload.get("end_datetime"):
            return "Missing required fields: start_datetime and end_datetime"
    return None


class IngestDatasetItemView(APIView):
    authentication_classes = [HeaderAPIKeyAuthentication]
    permission_classes = [HasAPIKey]

    def post(self, request, dataset_id: str):
        dataset = DatasetPage.objects.filter(dataset_id=dataset_id).first()
        if not dataset:
            return Response(
                {"detail": f"Unknown dataset_id '{dataset_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = request.data if isinstance(request.data, dict) else {}
        err = validate_payload_for_cadence(dataset.cadence, payload)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        run = IngestionRun.objects.create(
            dataset_id=dataset.dataset_id,
            cadence=dataset.cadence,
            status="accepted",
            payload=payload,
        )
        process_ingestion_run.delay(run.id)

        return Response(
            {"run_id": run.id, "status": run.status},
            status=status.HTTP_202_ACCEPTED,
        )






