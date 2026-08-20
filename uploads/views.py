import os
import uuid
from datetime import datetime, date, timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.cache import cache
from django.conf import settings

from .serializers import (
    PresignUploadRequestSerializer,
    PresignUploadResponseSerializer,
    DirectUploadRequestSerializer,
    DirectUploadResponseSerializer,
    UploadStatusResponseSerializer,
)
from .storage.minio import minio_client
from .tasks import upload_file_to_minio
from ingest.auth import HeaderAPIKeyAuthentication
from ingest.permissions import HasAPIKey
from catalog.models import DatasetPage
from ingest.api import validate_payload_for_cadence
from drf_spectacular.utils import extend_schema


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value

class PresignUploadView(APIView):
    """
    Returns a pre-signed PUT url for direct upload to MinIO + the resulting s3:// href.
    """
    authentication_classes = [HeaderAPIKeyAuthentication]
    permission_classes = [HasAPIKey]

    @extend_schema(
        request=PresignUploadRequestSerializer,
        responses=PresignUploadResponseSerializer,
        tags=["uploads"],
    )

    def post(self, request):
        s = PresignUploadRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        dataset_id = s.validated_data["dataset_id"]
        filename = s.validated_data["filename"]
        content_type = s.validated_data.get("content_type") or "application/octet-stream"

        bucket = os.getenv("MINIO_DEFAULT_BUCKET", "geodata")

        # Key convention (you can change this anytime)
        # geodata/<dataset_id>/YYYY/MM/<uuid>-<filename>
        now = datetime.now(timezone.utc)
        safe_name = filename.replace("/", "_").replace("\\", "_")
        key = f"{dataset_id}/{now:%Y/%m}/{uuid.uuid4()}-{safe_name}"

        client = minio_client()

        # Ensure bucket exists (dev-friendly)
        try:
            client.head_bucket(Bucket=bucket)
        except Exception:
            client.create_bucket(Bucket=bucket)

        # Presign URL for PUT
        upload_url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=60 * 15,  # 15 minutes
        )

        # Rewrite the host for browser access
        public_base = os.getenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000").rstrip("/")
        internal_base = os.environ["MINIO_ENDPOINT"].rstrip("/")
        upload_url_public = upload_url.replace(internal_base, public_base)

        href = f"s3://{bucket}/{key}"

        return Response(
            {
                "dataset_id": dataset_id,
                "bucket": bucket,
                "key": key,
                "href": href,
                "upload_url": upload_url_public,
                "expires_in": 900,
                "content_type": content_type,
            },
            status=status.HTTP_200_OK,
        )


class DirectUpFileUploadView(APIView):
    """
    Direct file upload through Django to MinIO (asynchronous).
    Accepts multipart form-data, saves temporarily, then uploads to MinIO in background.
    Returns a task ID that can be used to check upload status.
    """
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = [HeaderAPIKeyAuthentication]
    permission_classes = [HasAPIKey]

    @extend_schema(
        request=DirectUploadRequestSerializer,
        responses={202: DirectUploadResponseSerializer},
        tags=["uploads"],
    )
    def post(self, request):
        """
        Upload a file directly to MinIO through Django (async).
        Returns immediately with a task_id to poll for status.

        """
        serializer = DirectUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.validated_data.get("file")
        dataset_id = serializer.validated_data.get("dataset_id")
        auto_ingest = serializer.validated_data.get("auto_ingest", False)
        auto_extract = serializer.validated_data.get("auto_extract", True)
        
        if not file_obj:
            return Response(
                {"detail": "No file provided. Use 'file' field in form-data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not dataset_id:
            return Response(
                {"detail": "dataset_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ingest_payload = None
        if auto_ingest:
            dataset = DatasetPage.objects.filter(dataset_id=dataset_id).first()
            if not dataset:
                return Response(
                    {"detail": f"Unknown dataset_id '{dataset_id}'"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            stac_item = serializer.validated_data.get("stac_item")
            if stac_item:
                ingest_payload = {"stac_item": _json_safe(stac_item)}
            else:
                ingest_payload = {
                    "item_id": serializer.validated_data.get("item_id") or None,
                    "datetime": _json_safe(serializer.validated_data.get("datetime")),
                    "start_datetime": _json_safe(serializer.validated_data.get("start_datetime")),
                    "end_datetime": _json_safe(serializer.validated_data.get("end_datetime")),
                }
                bbox = serializer.validated_data.get("bbox")
                geometry = serializer.validated_data.get("geometry")
                if bbox is not None:
                    ingest_payload["bbox"] = _json_safe(bbox)
                if geometry is not None:
                    ingest_payload["geometry"] = _json_safe(geometry)
                err = validate_payload_for_cadence(dataset.cadence, ingest_payload)
                if err:
                    return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
                if not auto_extract:
                    if not ingest_payload.get("bbox") or not ingest_payload.get("geometry"):
                        return Response(
                            {"detail": "bbox and geometry are required when stac_item is not provided"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

        bucket = serializer.validated_data.get("bucket") or os.getenv("MINIO_DEFAULT_BUCKET", "geodata")
        
        # Generate key with same convention as presigned upload
        now = datetime.now(timezone.utc)
        safe_name = file_obj.name.replace("/", "_").replace("\\", "_")
        key = f"{dataset_id}/{now:%Y/%m}/{uuid.uuid4()}-{safe_name}"

        # Generate task ID
        task_id = str(uuid.uuid4())
        task_key = f"upload_task:{task_id}"

        # Save file temporarily
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f"{task_id}_{safe_name}")
        
        try:
            with open(temp_file_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)

            # Set initial status in cache
            cache.set(task_key, {
                "status": "pending",
                "bucket": bucket,
                "key": key,
                "auto_ingest": auto_ingest,
                "error": None,
            }, timeout=3600)

            # Queue upload task
            upload_file_to_minio.delay(
                temp_file_path,
                bucket,
                key,
                file_obj.content_type or "application/octet-stream",
                task_key,
                dataset_id,
                auto_ingest,
                ingest_payload,
                auto_extract,
            )

            status_url = request.build_absolute_uri(f"/api/uploads/status/{task_id}")

            return Response(
                {
                    "task_id": task_id,
                    "dataset_id": dataset_id,
                    "bucket": bucket,
                    "key": key,
                    "status": "pending",
                    "status_url": status_url,
                    "auto_ingest": auto_ingest,
                    "message": "File upload queued. Use status_url to check progress.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return Response(
                {"detail": f"Failed to queue upload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UploadStatusView(APIView):
    """
    Check the status of an async upload task.
    """
    authentication_classes = [HeaderAPIKeyAuthentication]
    permission_classes = [HasAPIKey]

    @extend_schema(
        responses={200: UploadStatusResponseSerializer},
        tags=["uploads"],
    )
    def get(self, request, task_id):
        """
        Get the status of an upload task.
        
        Example:
        ```bash
        curl -X GET http://localhost/api/uploads/status/{task_id} \
          -H "Authorization: Token your-token"
        ```
        
        Status values:
        - pending: Task is queued
        - processing: Upload in progress
        - completed: Upload successful (check 'href' field for S3 URI)
        - failed: Upload failed (check 'error' field)
        """
        task_key = f"upload_task:{task_id}"
        task_status = cache.get(task_key)
        
        if not task_status:
            return Response(
                {"detail": "Task not found or expired"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        return Response(task_status, status=status.HTTP_200_OK)
