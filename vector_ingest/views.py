from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated


from .models import VectorIngestJob
from .serializers import VectorIngestCreateSerializer, VectorIngestStatusSerializer
from .tasks import run_vector_ingest_pipeline
from ingest.auth import HeaderAPIKeyAuthentication

class VectorIngestUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    # authentication_classes = [HeaderAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    @extend_schema(
    request=VectorIngestCreateSerializer,
    responses={201: VectorIngestStatusSerializer},
    tags=["vector-ingest"],
    )
    def post(self, request):
        ser = VectorIngestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job = ser.save(schema_name="public", ingest_status="pending", archive_status="pending")

        run_vector_ingest_pipeline.delay(str(job.id))
        return Response(VectorIngestStatusSerializer(job).data, status=http_status.HTTP_201_CREATED)

class VectorIngestStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, job_id):
        job = get_object_or_404(VectorIngestJob, id=job_id)
        return Response(VectorIngestStatusSerializer(job).data)
