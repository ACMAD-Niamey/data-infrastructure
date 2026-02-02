import os
import uuid
from datetime import datetime, timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import PresignUploadRequestSerializer
from .storage.minio import minio_client
from ingest.auth import HeaderAPIKeyAuthentication
from ingest.permissions import HasAPIKey

class PresignUploadView(APIView):
    """
    Returns a pre-signed PUT url for direct upload to MinIO + the resulting s3:// href.
    """

    # keep your existing API key auth here
    authentication_classes = [HeaderAPIKeyAuthentication]
    permission_classes = [HasAPIKey]

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
