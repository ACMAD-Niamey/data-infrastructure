from datetime import date, datetime, timezone

from django.db import IntegrityError, transaction
from django.test import TestCase
from wagtail.models import Page

from catalog.models import DatasetPage, ProjectPage
from thredds_ingestion.models import (
    DownloadRun,
    DownloadRunItem,
    DownloadWorkflow,
    DownloadWorkflowFile,
)


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


class DownloadRunUniqueConstraintTests(TestCase):
    def setUp(self):
        self.dataset = _make_dataset()
        self.workflow = DownloadWorkflow.objects.create(
            name="ensemble5",
            source_base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5",
        )

    def test_duplicate_workflow_and_run_date_raises(self):
        DownloadRun.objects.create(workflow=self.workflow, run_date=date(2026, 8, 5))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DownloadRun.objects.create(workflow=self.workflow, run_date=date(2026, 8, 5))


class DownloadRunItemUniqueConstraintTests(TestCase):
    def setUp(self):
        self.dataset = _make_dataset()
        self.workflow = DownloadWorkflow.objects.create(
            name="ensemble5",
            source_base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5",
        )
        self.run = DownloadRun.objects.create(workflow=self.workflow, run_date=date(2026, 8, 5))
        self.workflow_file = DownloadWorkflowFile.objects.create(
            workflow=self.workflow,
            dataset=self.dataset,
            filename_pattern="5daymean_{run_date:%Y%m%d}.tif",
        )

    def _make_item(self, *, lead_hours=0, item_id="wwfd_5daymean_20260805"):
        return DownloadRunItem.objects.create(
            run=self.run,
            workflow_file=self.workflow_file,
            lead_hours=lead_hours,
            filename="5daymean_20260805.tif",
            source_url="https://sgbd.acmad.org/thredds/fileServer/.../5daymean_20260805.tif",
            item_id=item_id,
            valid_datetime=datetime(2026, 8, 5, tzinfo=timezone.utc),
        )

    def test_duplicate_run_workflow_file_lead_hours_raises(self):
        # This specifically validates the lead_hours=0 sentinel: two items for
        # the same workflow_file with no lead-hour dimension, in the same run,
        # must not both be creatable - a nullable lead_hours would silently
        # allow this on Postgres (NULL != NULL in a unique constraint).
        self._make_item(lead_hours=0, item_id="a")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_item(lead_hours=0, item_id="b")

    def test_distinct_lead_hours_are_allowed(self):
        self._make_item(lead_hours=24, item_id="a_24")
        self._make_item(lead_hours=96, item_id="a_96")
        self.assertEqual(DownloadRunItem.objects.count(), 2)

    def test_duplicate_item_id_raises(self):
        # Simulates a misconfigured item_id_pattern (e.g. missing {lead_hours})
        # producing the same id for two different resolved files.
        self._make_item(lead_hours=24, item_id="same-id")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_item(lead_hours=96, item_id="same-id")


class DownloadWorkflowFileLeadHoursListTests(TestCase):
    def setUp(self):
        self.dataset = _make_dataset()
        self.workflow = DownloadWorkflow.objects.create(
            name="ensemble5",
            source_base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5",
        )

    def test_blank_csv_yields_empty_list(self):
        wf = DownloadWorkflowFile.objects.create(
            workflow=self.workflow, dataset=self.dataset, filename_pattern="5daymean_{run_date:%Y%m%d}.tif"
        )
        self.assertEqual(wf.lead_hours_list(), [])

    def test_csv_parses_to_ints(self):
        wf = DownloadWorkflowFile.objects.create(
            workflow=self.workflow,
            dataset=self.dataset,
            filename_pattern="mix{run_date:%Y%m%d}_{lead_hours}.tif",
            lead_hours_csv="24, 96,144",
        )
        self.assertEqual(wf.lead_hours_list(), [24, 96, 144])
