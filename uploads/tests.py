import io
import os
import tempfile
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from ingest.models import APIKey, IngestionRun

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BBOX = [-17.5, 4.4, 51.4, 37.3]
GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [-17.5, 4.4], [-17.5, 37.3], [51.4, 37.3], [51.4, 4.4], [-17.5, 4.4]
    ]],
}


def _make_dataset(dataset_id="spi", cadence="daily"):
    ds = MagicMock()
    ds.dataset_id = dataset_id
    ds.cadence = cadence
    return ds


def _small_file(name="test.tif", content=b"FAKE"):
    return io.BytesIO(content), name


# ---------------------------------------------------------------------------
# PresignUploadView  POST /api/uploads/presign
# ---------------------------------------------------------------------------


class PresignUploadViewTests(TestCase):
    URL = "/api/uploads/presign"

    def setUp(self):
        self.client = APIClient()
        self.api_key = APIKey.objects.create(name="upload_user")
        self.client.credentials(HTTP_X_API_KEY=self.api_key.key)

    def test_returns_403_without_authentication(self):
        anon = APIClient()
        response = anon.post(self.URL, {}, format="json")
        self.assertIn(response.status_code, (401, 403))

    @patch("uploads.views.minio_client")
    def test_returns_200_with_presigned_url_fields(self, mock_mc):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "http://minio:9000/geodata/key?sig=xxx"
        mock_mc.return_value = mock_client

        with patch.dict(os.environ, {"MINIO_ENDPOINT": "http://minio:9000", "MINIO_ROOT_USER": "user", "MINIO_ROOT_PASSWORD": "pass"}):
            response = self.client.post(
                self.URL,
                {"dataset_id": "spi", "filename": "data.tif", "content_type": "image/tiff"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        for field in ("dataset_id", "bucket", "key", "href", "upload_url", "expires_in"):
            self.assertIn(field, response.data)

    @patch("uploads.views.minio_client")
    def test_key_follows_dataset_date_convention(self, mock_mc):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "http://minio:9000/geodata/key?sig=xxx"
        mock_mc.return_value = mock_client

        with patch.dict(os.environ, {"MINIO_ENDPOINT": "http://minio:9000", "MINIO_ROOT_USER": "user", "MINIO_ROOT_PASSWORD": "pass"}):
            response = self.client.post(
                self.URL,
                {"dataset_id": "ndvi", "filename": "file.tif"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        key = response.data["key"]
        self.assertTrue(key.startswith("ndvi/"))
        self.assertIn("file.tif", key)

    def test_missing_required_fields_returns_400(self):
        response = self.client.post(self.URL, {}, format="json")
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# DirectUpFileUploadView  POST /api/uploads/direct
# ---------------------------------------------------------------------------


class DirectUploadViewTests(TestCase):
    URL = "/api/uploads/direct"

    def setUp(self):
        self.client = APIClient()
        self.api_key = APIKey.objects.create(name="direct_user")
        self.client.credentials(HTTP_X_API_KEY=self.api_key.key)

    def test_returns_403_without_authentication(self):
        anon = APIClient()
        response = anon.post(self.URL, {})
        self.assertIn(response.status_code, (401, 403))

    @patch("uploads.views.upload_file_to_minio")
    def test_202_accepted_with_task_id_in_response(self, mock_task):
        data_stream, name = _small_file()
        response = self.client.post(
            self.URL,
            {"dataset_id": "spi", "file": (data_stream, name)},
            format="multipart",
        )
        self.assertEqual(response.status_code, 202)
        self.assertIn("task_id", response.data)

    @patch("uploads.views.upload_file_to_minio")
    def test_task_is_dispatched_on_success(self, mock_task):
        data_stream, name = _small_file()
        self.client.post(
            self.URL,
            {"dataset_id": "spi", "file": (data_stream, name)},
            format="multipart",
        )
        mock_task.delay.assert_called_once()

    def test_missing_file_returns_400(self):
        response = self.client.post(self.URL, {"dataset_id": "spi"}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_missing_dataset_id_returns_400(self):
        data_stream, name = _small_file()
        response = self.client.post(
            self.URL,
            {"file": (data_stream, name)},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# UploadStatusView  GET /api/uploads/status/<task_id>
# ---------------------------------------------------------------------------


class UploadStatusViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.api_key = APIKey.objects.create(name="status_user")
        self.client.credentials(HTTP_X_API_KEY=self.api_key.key)

    def test_pending_task_returns_status_pending(self):
        task_id = "abc-123"
        cache.set(f"upload_task:{task_id}", {"status": "pending", "error": None}, timeout=300)

        response = self.client.get(f"/api/uploads/status/{task_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "pending")

    def test_completed_task_returns_status_and_href(self):
        task_id = "abc-456"
        cache.set(
            f"upload_task:{task_id}",
            {"status": "completed", "href": "s3://geodata/spi/2026/04/file.tif", "error": None},
            timeout=300,
        )

        response = self.client.get(f"/api/uploads/status/{task_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "completed")
        self.assertIn("href", response.data)

    def test_unknown_task_id_returns_404(self):
        response = self.client.get("/api/uploads/status/does-not-exist-xyz")
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# upload_file_to_minio task (called via .apply() for synchronous execution)
# ---------------------------------------------------------------------------


class UploadFileToMinioTaskTests(TestCase):
    def _temp_file(self, content=b"TIFF DATA"):
        fd, path = tempfile.mkstemp(suffix=".tif")
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        return path

    def _run_task(self, file_path, bucket="geodata", key="spi/2026/04/file.tif",
                  auto_ingest=False, ingest_payload=None, auto_extract=False,
                  task_key="upload_task:test-id", dataset_id="spi"):
        from uploads.tasks import upload_file_to_minio
        return upload_file_to_minio.apply(args=(
            file_path, bucket, key, "image/tiff",
            task_key, dataset_id, auto_ingest, ingest_payload, auto_extract,
        ))

    @patch("uploads.tasks.minio_client")
    def test_file_is_uploaded_to_minio(self, mock_mc):
        mock_client = MagicMock()
        mock_mc.return_value = mock_client
        file_path = self._temp_file()

        self._run_task(file_path)

        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        self.assertEqual(call_kwargs["Key"], "spi/2026/04/file.tif")

    @patch("uploads.tasks.process_ingestion_run")
    @patch("uploads.tasks.DatasetPage")
    @patch("uploads.tasks.minio_client")
    def test_auto_ingest_true_creates_ingestion_run(self, mock_mc, mock_ds_cls, mock_task):
        mock_mc.return_value = MagicMock()
        mock_ds_cls.objects.filter.return_value.first.return_value = _make_dataset()
        file_path = self._temp_file()

        before = IngestionRun.objects.count()
        self._run_task(
            file_path,
            auto_ingest=True,
            ingest_payload={"datetime": "2026-04-15T00:00:00Z"},
        )
        self.assertEqual(IngestionRun.objects.count(), before + 1)

    @patch("uploads.tasks.minio_client")
    def test_auto_ingest_false_does_not_create_ingestion_run(self, mock_mc):
        mock_mc.return_value = MagicMock()
        file_path = self._temp_file()

        before = IngestionRun.objects.count()
        self._run_task(file_path, auto_ingest=False)
        self.assertEqual(IngestionRun.objects.count(), before)

    @patch("uploads.tasks._extract_raster_bbox_geometry")
    @patch("uploads.tasks.process_ingestion_run")
    @patch("uploads.tasks.DatasetPage")
    @patch("uploads.tasks.minio_client")
    def test_auto_extract_calls_gdal_when_bbox_missing(
        self, mock_mc, mock_ds_cls, mock_task, mock_extract
    ):
        mock_mc.return_value = MagicMock()
        mock_ds_cls.objects.filter.return_value.first.return_value = _make_dataset()
        mock_extract.return_value = (BBOX, GEOMETRY)
        file_path = self._temp_file()

        self._run_task(
            file_path,
            auto_ingest=True,
            auto_extract=True,
            ingest_payload={"datetime": "2026-04-15T00:00:00Z"},
        )
        mock_extract.assert_called_once()

    @patch("uploads.tasks.minio_client")
    def test_temp_file_is_deleted_after_success(self, mock_mc):
        mock_mc.return_value = MagicMock()
        file_path = self._temp_file()

        self._run_task(file_path)

        self.assertFalse(os.path.exists(file_path))

    @patch("uploads.tasks.minio_client")
    def test_cache_set_to_completed_on_success(self, mock_mc):
        mock_mc.return_value = MagicMock()
        task_key = "upload_task:test-cleanup"
        file_path = self._temp_file()

        self._run_task(file_path, task_key=task_key)

        status = cache.get(task_key)
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "completed")
