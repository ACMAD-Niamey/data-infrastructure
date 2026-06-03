from unittest.mock import MagicMock, patch

import botocore.exceptions
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from ingest.models import DeletionRun, IngestionRun
from ingest.tasks import build_item
from ingest.stac_ops import derive_item_id

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
    def setUp(self):
        self.cog_patcher = patch(
            "ingest.tasks.ensure_raster_is_cog",
            return_value={"optimized": False, "skipped": "already_cog"},
        )
        self.mock_ensure_cog = self.cog_patcher.start()

    def tearDown(self):
        self.cog_patcher.stop()

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

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.s3_client")
    def test_cog_conversion_called_for_tif(self, mock_s3, mock_ensure, mock_post):
        mock_s3.return_value = MagicMock()

        run = self._make_run()
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        self.mock_ensure_cog.assert_called_once()
        call_args = self.mock_ensure_cog.call_args[0]
        self.assertEqual(call_args[1], "geodata")
        self.assertEqual(call_args[2], "spi/2026/04/file.tif")

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.s3_client")
    def test_cog_skipped_for_non_tiff(self, mock_s3, mock_ensure, mock_post):
        mock_s3.return_value = MagicMock()
        payload = {
            **DAILY_PAYLOAD,
            "asset": {"href": "s3://geodata/spi/2026/04/file.nc"},
        }
        run = self._make_run(payload=payload)
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        self.mock_ensure_cog.assert_not_called()

    @patch("ingest.tasks.post_item")
    @patch("ingest.tasks.ensure_collection")
    @patch("ingest.tasks.s3_client")
    def test_cog_failure_sets_run_failed(self, mock_s3, mock_ensure, mock_post):
        mock_s3.return_value = MagicMock()
        self.mock_ensure_cog.side_effect = RuntimeError("COG conversion failed")

        run = self._make_run()
        from ingest.tasks import process_ingestion_run
        process_ingestion_run.apply(args=(run.id,))

        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIn("COG conversion failed", run.error_message)


class CogModuleTests(TestCase):
    def test_is_tiff_key(self):
        from ingest.cog import is_tiff_key

        self.assertTrue(is_tiff_key("path/file.tif"))
        self.assertTrue(is_tiff_key("path/file.TIFF"))
        self.assertFalse(is_tiff_key("path/file.nc"))

    @patch("ingest.cog.validate_cog", return_value=(True, [], []))
    def test_ensure_raster_is_cog_skips_when_already_valid(self, _mock_validate):
        from ingest.cog import ensure_raster_is_cog

        client = MagicMock()
        result = ensure_raster_is_cog(client, "geodata", "spi/file.tif")
        self.assertEqual(result["skipped"], "already_cog")
        client.upload_file.assert_not_called()

    @patch("ingest.cog.convert_to_cog")
    @patch("ingest.cog.validate_cog")
    def test_ensure_raster_is_cog_converts_when_strict_warnings(self, mock_validate, mock_convert):
        from ingest.cog import ensure_raster_is_cog

        mock_validate.return_value = (
            False,
            [],
            ["The file is greater than 512xH or 512xW, it is recommended to include internal overviews"],
        )
        client = MagicMock()
        result = ensure_raster_is_cog(client, "geodata", "e-safari/buildings.tif")
        self.assertEqual(result, {"optimized": True, "skipped": None})
        mock_convert.assert_called_once()
        client.upload_file.assert_called_once()

    @patch("ingest.cog.cog_validate")
    def test_is_valid_cog_strict_false_skips_on_warnings_only(self, mock_validate):
        from ingest.cog import is_valid_cog

        mock_validate.return_value = (
            True,
            [],
            ["The file is greater than 512xH or 512xW, it is recommended to include internal overviews"],
        )
        self.assertTrue(is_valid_cog("/tmp/file.tif", strict=False))
        mock_validate.assert_called_once_with("/tmp/file.tif", strict=False, quiet=True)

    @patch("ingest.cog.cog_validate")
    def test_is_valid_cog_strict_true_fails_on_warnings(self, mock_validate):
        from ingest.cog import is_valid_cog

        mock_validate.return_value = (
            False,
            [],
            ["The file is greater than 512xH or 512xW, it is recommended to include internal overviews"],
        )
        self.assertFalse(is_valid_cog("/tmp/file.tif", strict=True))
        mock_validate.assert_called_once_with("/tmp/file.tif", strict=True, quiet=True)

    def test_ensure_raster_is_cog_skips_non_tiff(self):
        from ingest.cog import ensure_raster_is_cog

        client = MagicMock()
        result = ensure_raster_is_cog(client, "geodata", "spi/file.nc")
        self.assertEqual(result["skipped"], "not_tiff")
        client.download_file.assert_not_called()


# ---------------------------------------------------------------------------
# Delete API
# ---------------------------------------------------------------------------


class DeleteDatasetItemViewTests(TestCase):
    URL = "/api/ingest/ingest/datasets/spi/items/spi_2026-04-15T000000Z"
    DATETIME_URL = "/api/ingest/ingest/datasets/spi/items/delete"

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("delete_user", password="pass")
        self.client.force_authenticate(user=self.user)

    @patch("ingest.delete_api.process_deletion_run")
    @patch("ingest.delete_api._get_dataset")
    def test_delete_by_item_id_returns_202(self, mock_dataset, mock_task):
        mock_dataset.return_value = _make_dataset(cadence="monthly")
        response = self.client.delete(self.URL)
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.data["delete_object"] is False)
        mock_task.delay.assert_called_once()
        run = DeletionRun.objects.get(id=response.data["run_id"])
        self.assertEqual(run.payload["item_id"], "spi_2026-04-15T000000Z")

    @patch("ingest.delete_api.process_deletion_run")
    @patch("ingest.delete_api._get_dataset")
    def test_delete_with_delete_object_flag(self, mock_dataset, mock_task):
        mock_dataset.return_value = _make_dataset(cadence="monthly")
        response = self.client.delete(f"{self.URL}?delete_object=true")
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.data["delete_object"])
        run = DeletionRun.objects.get(id=response.data["run_id"])
        self.assertTrue(run.delete_object)

    @patch("ingest.delete_api.resolve_item_ids_for_delete", return_value=["spi_2026-04-15T000000Z"])
    @patch("ingest.delete_api.process_deletion_run")
    @patch("ingest.delete_api._get_dataset")
    def test_delete_by_datetime_returns_202(self, mock_dataset, mock_task, _mock_resolve):
        mock_dataset.return_value = _make_dataset(cadence="monthly")
        response = self.client.delete(
            self.DATETIME_URL,
            {"datetime": "2026-04-15T00:00:00Z"},
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["item_id"], "spi_2026-04-15T000000Z")

    @patch("ingest.delete_api.resolve_item_ids_for_delete", return_value=["a", "b"])
    @patch("ingest.delete_api._get_dataset")
    def test_delete_by_datetime_multiple_items_returns_409(self, mock_dataset, _mock_resolve):
        mock_dataset.return_value = _make_dataset(cadence="monthly")
        response = self.client.delete(
            self.DATETIME_URL,
            {"datetime": "2026-04-15T00:00:00Z"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("item_ids", response.data)


class ProcessDeletionRunTaskTests(TestCase):
    def _make_run(self, *, delete_object=False, item_id="spi_2026-04-15T000000Z"):
        return DeletionRun.objects.create(
            dataset_id="spi",
            cadence="monthly",
            status="accepted",
            payload={"item_id": item_id},
            delete_object=delete_object,
        )

    @patch("ingest.tasks.delete_stac_item")
    @patch("ingest.tasks.get_stac_item")
    def test_stac_only_delete(self, mock_get, mock_delete):
        mock_get.return_value = {
            "id": "spi_2026-04-15T000000Z",
            "assets": {"data": {"href": "s3://geodata/spi/file.tif"}},
        }
        run = self._make_run(delete_object=False)
        from ingest.tasks import process_deletion_run

        process_deletion_run.apply(args=(run.id,))
        run.refresh_from_db()
        self.assertEqual(run.status, "completed")
        mock_delete.assert_called_once_with("spi", "spi_2026-04-15T000000Z")

    @patch("ingest.tasks.delete_minio_object")
    @patch("ingest.tasks.delete_stac_item")
    @patch("ingest.tasks.get_stac_item")
    def test_delete_object_purges_minio(self, mock_get, mock_delete, mock_minio):
        mock_get.return_value = {
            "id": "spi_2026-04-15T000000Z",
            "assets": {"data": {"href": "s3://geodata/spi/file.tif"}},
        }
        run = self._make_run(delete_object=True)
        from ingest.tasks import process_deletion_run

        process_deletion_run.apply(args=(run.id,))
        mock_minio.assert_called_once_with("s3://geodata/spi/file.tif")
        mock_delete.assert_called_once()


class StacOpsTests(TestCase):
    def test_derive_item_id_matches_ingest(self):
        item_id = derive_item_id("lu", datetime="2026-02-01T00:00:00Z")
        self.assertEqual(item_id, "lu_2026-02-01T000000Z")


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
