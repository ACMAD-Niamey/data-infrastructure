import io
import subprocess
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from vector_ingest.models import VectorIngestJob
from vector_ingest.utils import normalize_table_name

User = get_user_model()

# ---------------------------------------------------------------------------
# normalize_table_name  (pure unit tests)
# ---------------------------------------------------------------------------


class NormalizeTableNameTests(TestCase):
    def test_spaces_are_replaced_with_underscores(self):
        self.assertEqual(normalize_table_name("my dataset"), "my_dataset")

    def test_uppercase_is_lowercased(self):
        self.assertEqual(normalize_table_name("MyDataset"), "mydataset")

    def test_special_characters_are_stripped(self):
        result = normalize_table_name("data-set 2026!")
        self.assertRegex(result, r"^[a-z][a-z0-9_]*$")

    def test_name_is_truncated_to_63_chars(self):
        long_name = "a" * 100
        self.assertLessEqual(len(normalize_table_name(long_name)), 63)

    def test_empty_string_returns_default(self):
        result = normalize_table_name("")
        self.assertEqual(result, "dataset")

    def test_hyphens_become_underscores(self):
        self.assertEqual(normalize_table_name("my-table"), "my_table")


# ---------------------------------------------------------------------------
# VectorIngestUploadView  POST /api/vector/vector/ingest/
# ---------------------------------------------------------------------------


class VectorIngestJobCreateTests(TestCase):
    URL = "/api/vector/vector/ingest/"

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("vec_user", password="pass")
        self.client.force_authenticate(user=self.user)

    def test_returns_403_without_authentication(self):
        anon = APIClient()
        response = anon.post(self.URL, {})
        self.assertIn(response.status_code, (401, 403))

    @patch("vector_ingest.views.run_vector_ingest_pipeline")
    def test_201_with_job_id_returned(self, mock_task):
        geojson = io.BytesIO(b'{"type":"FeatureCollection","features":[]}')
        response = self.client.post(
            self.URL,
            {
                "dataset_name": "Test Dataset",
                "table_name": "test_table",
                "srid": 4326,
                "upload": (geojson, "data.geojson"),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)

    @patch("vector_ingest.views.run_vector_ingest_pipeline")
    def test_pipeline_task_is_dispatched_on_create(self, mock_task):
        geojson = io.BytesIO(b'{"type":"FeatureCollection","features":[]}')
        self.client.post(
            self.URL,
            {
                "dataset_name": "Test Dataset",
                "table_name": "test_table",
                "srid": 4326,
                "upload": (geojson, "data.geojson"),
            },
            format="multipart",
        )
        mock_task.delay.assert_called_once()

    def test_missing_file_returns_400(self):
        response = self.client.post(
            self.URL,
            {"dataset_name": "Test", "table_name": "test_table"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# VectorIngestStatusView  GET /api/vector/vector/ingest/<job_id>/status/
# ---------------------------------------------------------------------------


class VectorIngestJobStatusTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("vec_status_user", password="pass")
        self.client.force_authenticate(user=self.user)

    def _create_job(self, ingest_status="pending"):
        return VectorIngestJob.objects.create(
            dataset_name="Test",
            table_name="test_table",
            schema_name="public",
            srid=4326,
            ingest_status=ingest_status,
            archive_status="pending",
            upload="vector_uploads/test/test.geojson",
        )

    def test_pending_job_returns_ingest_status_pending(self):
        job = self._create_job(ingest_status="pending")
        response = self.client.get(f"/api/vector/vector/ingest/{job.id}/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ingest_status"], "pending")

    def test_ready_job_returns_status_ready(self):
        job = self._create_job(ingest_status="ready")
        job.row_count = 500
        job.save()
        response = self.client.get(f"/api/vector/vector/ingest/{job.id}/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ingest_status"], "ready")
        self.assertEqual(response.data["row_count"], 500)

    def test_unknown_job_id_returns_404(self):
        response = self.client.get(f"/api/vector/vector/ingest/{uuid.uuid4()}/status/")
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# ingest_to_postgis task
# ---------------------------------------------------------------------------


class IngestToPostGISTaskTests(TestCase):
    def _create_job(self):
        return VectorIngestJob.objects.create(
            dataset_name="Test",
            table_name="test_table",
            schema_name="public",
            srid=4326,
            ingest_status="pending",
            archive_status="pending",
            upload="vector_uploads/test/test.geojson",
        )

    @patch("vector_ingest.tasks.connections")
    @patch("vector_ingest.tasks.subprocess.run")
    def test_successful_ingest_sets_status_ready(self, mock_run, mock_conns):
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: mock_cursor
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = (100,)
        mock_conns.__getitem__.return_value.cursor.return_value = mock_cursor

        job = self._create_job()
        # Patch upload.path to a known value (file existence is checked)
        with patch.object(type(job.upload), "path", new_callable=lambda: property(lambda self: "/tmp/fake.geojson")):
            with patch("os.path.exists", return_value=True):
                from vector_ingest.tasks import ingest_to_postgis
                ingest_to_postgis.apply(args=(str(job.id),))

        job.refresh_from_db()
        self.assertEqual(job.ingest_status, "ready")

    @patch("vector_ingest.tasks.connections")
    @patch("vector_ingest.tasks.subprocess.run")
    def test_ogr2ogr_failure_sets_status_failed(self, mock_run, mock_conns):
        mock_run.return_value = MagicMock(returncode=1, stderr="ERROR: bad file", stdout="")
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: mock_cursor
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conns.__getitem__.return_value.cursor.return_value = mock_cursor

        job = self._create_job()
        with patch.object(type(job.upload), "path", new_callable=lambda: property(lambda self: "/tmp/fake.geojson")):
            with patch("os.path.exists", return_value=True):
                from vector_ingest.tasks import ingest_to_postgis
                try:
                    ingest_to_postgis.apply(args=(str(job.id),))
                except Exception:
                    pass  # task re-raises after setting failed

        job.refresh_from_db()
        self.assertEqual(job.ingest_status, "failed")
        self.assertIn("ogr2ogr failed", job.ingest_error)

    @patch("vector_ingest.tasks.connections")
    @patch("vector_ingest.tasks.subprocess.run")
    def test_ogr2ogr_called_with_correct_table_and_srid(self, mock_run, mock_conns):
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: mock_cursor
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = (0,)
        mock_conns.__getitem__.return_value.cursor.return_value = mock_cursor

        job = self._create_job()
        with patch.object(type(job.upload), "path", new_callable=lambda: property(lambda self: "/tmp/fake.geojson")):
            with patch("os.path.exists", return_value=True):
                from vector_ingest.tasks import ingest_to_postgis
                ingest_to_postgis.apply(args=(str(job.id),))

        cmd = mock_run.call_args[0][0]
        self.assertIn("ogr2ogr", cmd)
        self.assertIn("EPSG:4326", " ".join(cmd))
        self.assertIn("public.test_table", " ".join(cmd))

    @patch("vector_ingest.tasks.connections")
    @patch("vector_ingest.tasks.subprocess.run")
    def test_row_count_updated_after_successful_ingest(self, mock_run, mock_conns):
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: mock_cursor
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = (250,)
        mock_conns.__getitem__.return_value.cursor.return_value = mock_cursor

        job = self._create_job()
        with patch.object(type(job.upload), "path", new_callable=lambda: property(lambda self: "/tmp/fake.geojson")):
            with patch("os.path.exists", return_value=True):
                from vector_ingest.tasks import ingest_to_postgis
                ingest_to_postgis.apply(args=(str(job.id),))

        job.refresh_from_db()
        self.assertEqual(job.row_count, 250)


# ---------------------------------------------------------------------------
# archive_to_minio task
# ---------------------------------------------------------------------------


class ArchiveToMinioTaskTests(TestCase):
    def _create_job(self):
        return VectorIngestJob.objects.create(
            dataset_name="Archive Test",
            table_name="archive_table",
            schema_name="public",
            srid=4326,
            ingest_status="ready",
            archive_status="pending",
            upload="vector_uploads/test/archive.geojson",
        )

    @patch("vector_ingest.tasks._minio_client")
    def test_successful_archive_sets_archive_uri(self, mock_mc):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_mc.return_value = mock_client

        job = self._create_job()
        with patch.object(type(job.upload), "path", new_callable=lambda: property(lambda self: "/tmp/archive.geojson")):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.basename", return_value="archive.geojson"):
                    from vector_ingest.tasks import archive_to_minio
                    archive_to_minio.apply(args=(str(job.id),))

        job.refresh_from_db()
        self.assertEqual(job.archive_status, "ready")
        self.assertTrue(job.archive_uri.startswith("s3://"))

    @patch("vector_ingest.tasks._minio_client")
    def test_minio_error_sets_archive_status_failed_without_raising(self, mock_mc):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.fput_object.side_effect = Exception("MinIO connection refused")
        mock_mc.return_value = mock_client

        job = self._create_job()
        with patch.object(type(job.upload), "path", new_callable=lambda: property(lambda self: "/tmp/archive.geojson")):
            with patch("os.path.exists", return_value=True):
                from vector_ingest.tasks import archive_to_minio
                archive_to_minio.apply(args=(str(job.id),))

        job.refresh_from_db()
        self.assertEqual(job.archive_status, "failed")
        self.assertIn("MinIO connection refused", job.archive_error)

    @patch("vector_ingest.tasks._minio_client")
    def test_archive_creates_bucket_if_missing(self, mock_mc):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_mc.return_value = mock_client

        job = self._create_job()
        with patch.object(type(job.upload), "path", new_callable=lambda: property(lambda self: "/tmp/archive.geojson")):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.basename", return_value="archive.geojson"):
                    from vector_ingest.tasks import archive_to_minio
                    archive_to_minio.apply(args=(str(job.id),))

        mock_client.make_bucket.assert_called_once()
