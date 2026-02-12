from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from catalog.models import DatasetPage
from .auth import HeaderAPIKeyAuthentication
from .models import IngestionRun
from .permissions import HasAPIKey
from .serializers import IngestRequestSerializer, IngestResponseSerializer

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
    """
    Ingest a dataset item into STAC catalog.
    
    This endpoint expects the file to already exist in MinIO storage.
    It validates the S3 path, creates necessary STAC collections,
    and posts the item metadata to the pgSTAC catalog.
    """
    authentication_classes = [HeaderAPIKeyAuthentication]
    permission_classes = [HasAPIKey]

    @extend_schema(
        request=IngestRequestSerializer,
        responses={202: IngestResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="dataset_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="The dataset ID (STAC collection name)"
            )
        ],
        tags=["ingest"],
        description="""
        Ingest a dataset item into the STAC catalog.
        
        **Prerequisites:**
        - File must already be uploaded to MinIO
        - Dataset must exist in Django admin
        
        **Workflow:**
        1. Upload file to MinIO (via /api/uploads/ or manually)
        2. Call this endpoint with the S3 path and metadata
        3. System validates file exists in MinIO
        4. Creates STAC collection if needed
        5. Posts STAC item to pgSTAC catalog
        
        **Cadence-specific requirements:**
        - `daily` or `monthly`: Requires `datetime` field
        - `dekadal` or `seasonal`: Requires `start_datetime` and `end_datetime` fields
        
        **Example for monthly data:**
        ```json
        {
          "asset": {
            "href": "s3://geodata/trees/2025/12/file.tif"
          },
          "datetime": "2025-12-15T00:00:00Z",
          "bbox": [-180, -90, 180, 90],
          "geometry": {
            "type": "Polygon",
            "coordinates": [[...]]
          }
        }
        ```
        """
    )
    def post(self, request, dataset_id: str):
        dataset = DatasetPage.objects.filter(dataset_id=dataset_id).first()
        if not dataset:
            return Response(
                {"detail": f"Unknown dataset_id '{dataset_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = IngestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        
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






