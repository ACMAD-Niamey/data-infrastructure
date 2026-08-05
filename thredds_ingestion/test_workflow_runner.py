from datetime import date
from unittest.mock import patch

from django.test import TestCase
from wagtail.models import Page

from catalog.models import DatasetPage, ProjectPage
from ingest.models import IngestionRun
from thredds_ingestion.models import DownloadRun, DownloadRunItem, DownloadWorkflow, DownloadWorkflowFile
from thredds_ingestion.services import workflow_runner

RUN_DATE = date(2026, 8, 5)


def _make_dataset(dataset_id="wwfd_5daymean") -> DatasetPage:
    root = Page.get_first_root_node()
    project = root.add_child(instance=ProjectPage(title="Test Project", slug=f"project-{dataset_id}"))
    dataset = DatasetPage(
        title="Test Dataset",
        slug=f"dataset-{dataset_id}",
        dataset_id=dataset_id,
        dataset_type="raster",
        cadence="daily",
    )
    project.add_child(instance=dataset)
    return dataset


class WorkflowRunnerTestCase(TestCase):
    def setUp(self):
        self.dataset = _make_dataset()
        self.workflow = DownloadWorkflow.objects.create(
            name="ensemble5",
            source_base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5",
        )
        self.run = DownloadRun.objects.create(workflow=self.workflow, run_date=RUN_DATE)
        self.workflow_file = DownloadWorkflowFile.objects.create(
            workflow=self.workflow,
            dataset=self.dataset,
            filename_pattern="5daymean_{run_date:%Y%m%d}.tif",
        )


class NotYetAvailableTests(WorkflowRunnerTestCase):
    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists", return_value=False)
    @patch("thredds_ingestion.services.workflow_runner.ingest_bridge.push_to_ingest")
    @patch("thredds_ingestion.services.workflow_runner.ingest_bridge.upload_file")
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.exists", return_value=False)
    def test_not_yet_available_does_not_download_or_ingest(
        self, mock_exists, mock_upload, mock_push, _mock_stac
    ):
        item = workflow_runner.process_item(self.run, self.workflow_file, 0)

        self.assertEqual(item.status, DownloadRunItem.Status.NOT_YET_AVAILABLE)
        self.assertEqual(item.attempt_count, 1)
        mock_upload.assert_not_called()
        mock_push.assert_not_called()


class AlreadyCompletedSkipTests(WorkflowRunnerTestCase):
    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists")
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.exists")
    def test_already_completed_item_is_not_reprocessed(self, mock_exists, mock_stac):
        DownloadRunItem.objects.create(
            run=self.run,
            workflow_file=self.workflow_file,
            lead_hours=0,
            filename="5daymean_20260805.tif",
            source_url="https://example.com/5daymean_20260805.tif",
            item_id="wwfd_5daymean_20260805",
            valid_datetime="2026-08-05T00:00:00Z",
            status=DownloadRunItem.Status.COMPLETED,
        )

        item = workflow_runner.process_item(self.run, self.workflow_file, 0)

        self.assertEqual(item.status, DownloadRunItem.Status.COMPLETED)
        mock_exists.assert_not_called()
        mock_stac.assert_not_called()


class StacReconciliationSkipTests(WorkflowRunnerTestCase):
    @patch("thredds_ingestion.services.workflow_runner.ingest_bridge.push_to_ingest")
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.exists")
    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists", return_value=True)
    def test_existing_stac_item_is_reconciled_without_download(self, mock_stac, mock_exists, mock_push):
        item = workflow_runner.process_item(self.run, self.workflow_file, 0)

        self.assertEqual(item.status, DownloadRunItem.Status.SKIPPED)
        mock_exists.assert_not_called()
        mock_push.assert_not_called()


class DownstreamConflictReconciliationTests(WorkflowRunnerTestCase):
    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists")
    @patch("thredds_ingestion.services.workflow_runner.ingest_bridge.push_to_ingest")
    @patch("thredds_ingestion.services.workflow_runner.ingest_bridge.upload_file", return_value="s3://geodata/x.tif")
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.download_to_path")
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.exists", return_value=True)
    def test_downstream_409_reconciled_as_success(
        self, mock_thredds_exists, mock_download, mock_upload, mock_push, mock_stac
    ):
        # First call (inside process_item after the failed ingest) confirms
        # the item is not present yet (initial fast-path check), second call
        # (the reconciliation check after a 409) confirms it now exists.
        mock_stac.side_effect = [False, True]

        failed_run = IngestionRun.objects.create(
            dataset_id=self.dataset.dataset_id,
            cadence="daily",
            status="failed",
            error_message="STAC item POST failed 409: Conflict",
        )
        mock_push.return_value = failed_run

        item = workflow_runner.process_item(self.run, self.workflow_file, 0)

        self.assertEqual(item.status, DownloadRunItem.Status.COMPLETED)
        self.assertIn("409", item.error_message)


class RealFailureTests(WorkflowRunnerTestCase):
    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists", return_value=False)
    @patch("thredds_ingestion.services.workflow_runner.ingest_bridge.push_to_ingest")
    @patch("thredds_ingestion.services.workflow_runner.ingest_bridge.upload_file", return_value="s3://geodata/x.tif")
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.download_to_path")
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.exists", return_value=True)
    def test_non_conflict_failure_is_a_real_failure(
        self, mock_thredds_exists, mock_download, mock_upload, mock_push, mock_stac
    ):
        failed_run = IngestionRun.objects.create(
            dataset_id=self.dataset.dataset_id,
            cadence="daily",
            status="failed",
            error_message="COG conversion failed: bad raster",
        )
        mock_push.return_value = failed_run

        item = workflow_runner.process_item(self.run, self.workflow_file, 0)

        self.assertEqual(item.status, DownloadRunItem.Status.FAILED)
        self.assertIn("COG conversion failed", item.error_message)


class NoLeadHoursMappingTests(WorkflowRunnerTestCase):
    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists", return_value=True)
    def test_resolves_to_single_item_with_lead_hours_zero(self, _mock_stac):
        item = workflow_runner.process_item(self.run, self.workflow_file, 0)

        self.assertEqual(item.lead_hours, 0)
        self.assertNotIn("None", item.filename)
        self.assertNotIn("None", item.item_id)


class ExecuteAggregationTests(WorkflowRunnerTestCase):
    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists", return_value=True)
    def test_execute_marks_run_completed_when_all_items_reconciled(self, _mock_stac):
        run = workflow_runner.execute(self.run)

        self.assertEqual(run.status, DownloadRun.Status.COMPLETED)
        self.assertEqual(run.total_files, 1)
        self.assertEqual(run.completed_files, 1)

    @patch("thredds_ingestion.services.workflow_runner._stac_item_exists", return_value=False)
    @patch("thredds_ingestion.services.workflow_runner.thredds_client.exists", return_value=False)
    def test_execute_marks_run_partial_when_not_yet_available(self, _mock_exists, _mock_stac):
        run = workflow_runner.execute(self.run)

        self.assertEqual(run.status, DownloadRun.Status.PARTIAL)
        self.assertEqual(run.not_yet_available_files, 1)
