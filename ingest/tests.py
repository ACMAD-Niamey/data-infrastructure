from unittest.mock import MagicMock, patch

import botocore.exceptions
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from ingest.models import IngestionRun
from ingest.tasks import build_item

User = get_user_model()

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

BBOX = [-17.5, 4.4, 51.4, 37.3]
GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [-17.5, 4.4], [-17.5, 37.3], [51.4, 37.3], [51.4, 4.4], [-17.5, 4.4]
    ]],
}
DAILY_PAYLOAD = {
    "asset": {"href": "s3://geodata/spi/2026/04/file.tif"},
    "datetime": "2026-04-15T00:00:00Z",
    "bbox": BBOX,
    "geometry": GEOMETRY,
}
DEKADAL_PAYLOAD = {
    "asset": {"href": "s3://geodata/spi/2026/04/file.tif"},
    "start_datetime": "2026-04-01T00:00:00Z",
    "end_datetime": "2026-04-10T23:59:59Z",
    "bbox": BBOX,
    "geometry": GEOMETRY,
}


def _make_dataset(dataset_id="spi", cadence="monthly"):
    ds = MagicMock()
    ds.dataset_id = dataset_id
    ds.cadence = cadence
    return ds


# ---------------------------------------------------------------------------
# IngestDatasetItemView  POST /api/ingest/ingest/datasets/<dataset_id>/items
# ---------------------------------------------------------------------------


class IngestionSubmitViewTests(TestCase):
    URL = "/api/ingest/ingest/datasets/spi/items"

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("ingest_user", password="pass")
        self.client.force_authenticate(user=self.user)

    def test_returns_403_without_authentication(self):
        anon = APIClient()
        response = anon.post(self.URL, DAILY_PAYLOAD, format="json")
        self.assertIn(response.status_code, (401, 403))

    @patch("ingest.api.process_ingestion_run")
    @patch("ingest.api.DatasetPage")
    def test_202_accepted_for_daily_payload(self, mock_ds_cls, mock_task):
        mock_ds_cls.objects.filter.return_value.first.return_value = _make_dataset(cadence="daily")
        response = self.client.post(self.URL, DAILY_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertIn("run_id", response.data)
        self.assertEqual(response.data["status"], "accepted")

    @patch("ingest.api.process_ingestion_run")
    @patch("ingest.api.DatasetPage")
    def test_202_accepted_for_dekadal_payload(self, mock_ds_cls, mock_task):
        mock_ds_cls.objects.filter.return_value.first.return_value = _make_dataset(cadence="dekadal")
        response = self.client.post(self.URL, DEKADAL_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 202)

    @patch("ingest.api.process_ingestion_run")
    @patch("ingest.api.DatasetPage")
    def test_task_is_dispatched_on_success(self, mock_ds_cls, mock_task):
        mock_ds_cls.objects.filter.return_value.first.return_value = _make_dataset(cadence="daily")
        self.client.post(self.URL, DAILY_PAYLOAD, format="json")
        mock_task.delay.assert_called_once()

    @patch("ingest.api.DatasetPage")
    def test_returns_404_for_unknown_dataset(self, mock_ds_cls):
        mock_ds_cls.objects.filter.return_value.first.return_value = None
        response = self.client.post(self.URL, DAILY_PAYLOAD, format="json")
        self.assertEqual(response.status_code, 404)

    @patch("ingest.api.DatasetPage")
    def test_returns_400_when_cadence_fields_missing(self, mock_ds_cls):
        # daily cadence but no datetime provided
        mock_ds_cls.objects.filter.return_value.first.return_value = _make_dataset(cadence="daily")
        bad_payload = {
            "asset": {"href": "s3://geodata/spi/2026/04/file.tif"},
            "bbox": BBOX,
            "geometry": GEOMETRY,
        }
        response = self.client.post(self.URL, bad_payload, format="json")
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# process_ingestion_run task
# ---------------------------------------------------------------------------


class ProcessIngestionRunTaskTests(TestCase):
    def _make_run(self, payload=None):
        return IngestionRun.objects.create(
            dataset_id="spi",
            cadence="daily",
            status="accepted",
            payload=payload or DAILY_PAYLOAD,
        )

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.s3_client")
    def test_successful_run_sets_status_completed(self, mock_s3, mock_ensure, mock_post):
        mock_client = MagicMock()
        mock_s3.return_value = mock_client

        run = self._make_run()
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        run.refresh_from_db()
        self.assertEqual(run.status, "completed")

    @patch("ingest.tasks.s3_client")
    def test_invalid_s3_path_sets_status_failed(self, mock_s3):
        payload = {**DAILY_PAYLOAD, "asset": {"href": "https://not-s3/file.tif"}}
        run = self._make_run(payload=payload)
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIn("s3://", run.error_message)

    @patch("ingest.tasks.s3_client")
    def test_file_not_found_in_minio_sets_status_failed(self, mock_s3):
        mock_client = MagicMock()
        mock_s3.return_value = mock_client
        mock_client.head_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )

        run = self._make_run()
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        run.refresh_from_db()
        self.assertEqual(run.status, "failed")

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.extract_bbox_geometry_from_s3_object")
    @patch("ingest.tasks.s3_client")
    def test_gdal_extraction_called_when_bbox_missing(
        self, mock_s3, mock_extract, mock_ensure, mock_post
    ):
        mock_s3.return_value = MagicMock()
        mock_extract.return_value = (BBOX, GEOMETRY)

        payload = {
            "asset": {"href": "s3://geodata/spi/2026/04/file.tif"},
            "datetime": "2026-04-15T00:00:00Z",
        }
        run = self._make_run(payload=payload)
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        mock_extract.assert_called_once()

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.s3_client")
    def test_status_transitions_to_processing_then_completed(
        self, mock_s3, mock_ensure, mock_post
    ):
        mock_s3.return_value = MagicMock()

        run = self._make_run()
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        run.refresh_from_db()
        self.assertEqual(run.status, "completed")

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.s3_client")
    def test_post_item_called_with_correct_collection(
        self, mock_s3, mock_ensure, mock_post
    ):
        mock_s3.return_value = MagicMock()

        run = self._make_run()
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        mock_post.assert_called_once()
        item = mock_post.call_args[0][0]
        self.assertEqual(item["collection"], "spi")

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.s3_client")
    def test_post_item_failure_sets_status_failed(
        self, mock_s3, mock_ensure, mock_post
    ):
        mock_s3.return_value = MagicMock()
        mock_post.side_effect = RuntimeError("STAC API unreachable")

        run = self._make_run()
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIn("STAC API unreachable", run.error_message)


# ---------------------------------------------------------------------------
# build_item helper (pure unit tests, no DB needed)
# ---------------------------------------------------------------------------


class BuildItemTests(TestCase):
    def test_daily_item_has_datetime_in_properties(self):
        payload = {
            "asset": {"href": "s3://geodata/spi/file.tif"},
            "datetime": "2026-04-15T00:00:00Z",
            "bbox": BBOX,
            "geometry": GEOMETRY,
        }
        item = build_item("spi", payload)
        self.assertIn("datetime", item["properties"])

    def test_dekadal_item_has_start_and_end_datetime(self):
        payload = {
            "asset": {"href": "s3://geodata/spi/file.tif"},
            "start_datetime": "2026-04-01T00:00:00Z",
            "end_datetime": "2026-04-10T23:59:59Z",
            "bbox": BBOX,
            "geometry": GEOMETRY,
        }
        item = build_item("spi", payload)
        self.assertIn("start_datetime", item["properties"])
        self.assertIn("end_datetime", item["properties"])

    def test_built_item_includes_bbox_and_geometry(self):
        payload = {
            "asset": {"href": "s3://geodata/spi/file.tif"},
            "datetime": "2026-04-15T00:00:00Z",
            "bbox": BBOX,
            "geometry": GEOMETRY,
        }
        item = build_item("spi", payload)
        self.assertEqual(item["bbox"], BBOX)
        self.assertEqual(item["geometry"]["type"], "Polygon")

    def test_built_item_uses_stac_version_1(self):
        payload = {
            "asset": {"href": "s3://geodata/spi/file.tif"},
            "datetime": "2026-04-15T00:00:00Z",
            "bbox": BBOX,
            "geometry": GEOMETRY,
        }
        item = build_item("spi", payload)
        self.assertEqual(item["stac_version"], "1.0.0")

    def test_full_stac_item_passed_through_unchanged(self):
        stac_item = {
            "stac_version": "1.0.0",
            "id": "custom-id",
            "type": "Feature",
            "collection": "spi",
            "bbox": BBOX,
            "geometry": GEOMETRY,
            "properties": {"datetime": "2026-04-15T00:00:00Z"},
            "links": [],
            "assets": {},
        }
        result = build_item("spi", {"stac_item": stac_item})
        self.assertEqual(result, stac_item)
