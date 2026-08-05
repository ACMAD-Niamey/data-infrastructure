import datetime as dt
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase

from thredds_ingestion.models import DownloadRun, DownloadWorkflow
from thredds_ingestion.tasks import run_due_download_workflows

FIXED_NOW = dt.datetime(2026, 8, 5, 10, 0, 0, tzinfo=dt_timezone.utc)


def _workflow(**overrides):
    defaults = dict(
        name="ensemble5",
        source_base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5",
        schedule_hour_utc=0,
        schedule_minute_utc=0,
        retry_until_hour_utc=23,
        retry_interval_minutes=30,
        catch_up_days=2,
        enabled=True,
    )
    defaults.update(overrides)
    return DownloadWorkflow.objects.create(**defaults)


@patch("thredds_ingestion.tasks.timezone.now", return_value=FIXED_NOW)
class RunDueDownloadWorkflowsTests(TestCase):
    @patch("thredds_ingestion.tasks.process_download_run.delay")
    def test_dispatches_today_and_catch_up_days_when_today_is_due(self, mock_delay, _mock_now):
        workflow = _workflow(catch_up_days=2)

        run_due_download_workflows()

        self.assertEqual(mock_delay.call_count, 3)  # today + 2 catch-up days
        dates = sorted(DownloadRun.objects.filter(workflow=workflow).values_list("run_date", flat=True))
        today = FIXED_NOW.date()
        self.assertEqual(dates, [today - dt.timedelta(days=2), today - dt.timedelta(days=1), today])

    @patch("thredds_ingestion.tasks.process_download_run.delay")
    def test_today_skipped_outside_schedule_window_but_catch_up_days_still_dispatched(self, mock_delay, _mock_now):
        # cutoff = today at 00:00, FIXED_NOW is 10:00 -> today is NOT due.
        workflow = _workflow(retry_until_hour_utc=0, catch_up_days=2)

        run_due_download_workflows()

        self.assertEqual(mock_delay.call_count, 2)  # only the 2 catch-up days, not today
        dates = sorted(DownloadRun.objects.filter(workflow=workflow).values_list("run_date", flat=True))
        today = FIXED_NOW.date()
        self.assertEqual(dates, [today - dt.timedelta(days=2), today - dt.timedelta(days=1)])

    @patch("thredds_ingestion.tasks.process_download_run.delay")
    def test_already_completed_run_is_not_redispatched(self, mock_delay, _mock_now):
        workflow = _workflow(catch_up_days=0)
        DownloadRun.objects.create(
            workflow=workflow, run_date=FIXED_NOW.date(), status=DownloadRun.Status.COMPLETED
        )

        run_due_download_workflows()

        mock_delay.assert_not_called()

    @patch("thredds_ingestion.tasks.process_download_run.delay")
    def test_recently_attempted_run_is_throttled(self, mock_delay, _mock_now):
        workflow = _workflow(catch_up_days=0, retry_interval_minutes=30)
        DownloadRun.objects.create(
            workflow=workflow,
            run_date=FIXED_NOW.date(),
            status=DownloadRun.Status.PARTIAL,
            last_attempted_at=FIXED_NOW - dt.timedelta(minutes=5),
        )

        run_due_download_workflows()

        mock_delay.assert_not_called()

    @patch("thredds_ingestion.tasks.process_download_run.delay")
    def test_stale_partial_run_past_retry_interval_is_redispatched(self, mock_delay, _mock_now):
        workflow = _workflow(catch_up_days=0, retry_interval_minutes=30)
        DownloadRun.objects.create(
            workflow=workflow,
            run_date=FIXED_NOW.date(),
            status=DownloadRun.Status.PARTIAL,
            last_attempted_at=FIXED_NOW - dt.timedelta(minutes=45),
        )

        run_due_download_workflows()

        mock_delay.assert_called_once()

    @patch("thredds_ingestion.tasks.process_download_run.delay")
    def test_disabled_workflow_is_ignored(self, mock_delay, _mock_now):
        _workflow(enabled=False)

        run_due_download_workflows()

        mock_delay.assert_not_called()
