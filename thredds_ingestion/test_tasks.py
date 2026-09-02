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


def _dispatched_run_dates(workflow) -> list[dt.date]:
    return sorted(DownloadRun.objects.filter(workflow=workflow).values_list("run_date", flat=True))


# FIXED_NOW is 2026-08-05.
@patch("thredds_ingestion.tasks.timezone.now", return_value=FIXED_NOW)
@patch("thredds_ingestion.tasks.process_download_run.delay")
class MonthlyCadenceTests(TestCase):
    def _workflow(self, **overrides):
        defaults = dict(cadence=DownloadWorkflow.Cadence.MONTHLY, catch_up_days=2)
        defaults.update(overrides)
        return _workflow(**defaults)

    def test_newest_target_is_last_month_and_run_dates_are_first_of_month(self, mock_delay, _now):
        # publish window open (schedule_day_of_month=1, today is the 5th).
        workflow = self._workflow(schedule_day_of_month=1)

        run_due_download_workflows()

        dates = _dispatched_run_dates(workflow)
        self.assertEqual(dates, [dt.date(2026, 6, 1), dt.date(2026, 7, 1)])  # last month + 1 catch-up month
        self.assertTrue(all(d.day == 1 for d in dates))

    def test_newest_month_gated_out_before_publish_day(self, mock_delay, _now):
        # schedule_day_of_month=20 but today is the 5th -> July not attempted,
        # only the always-safe older catch-up month.
        workflow = self._workflow(schedule_day_of_month=20)

        run_due_download_workflows()

        self.assertEqual(_dispatched_run_dates(workflow), [dt.date(2026, 6, 1)])

    def test_newest_month_gated_out_after_retry_window(self, mock_delay, _now):
        workflow = self._workflow(schedule_day_of_month=1, retry_window_days=2)  # window [08-01, 08-03]

        run_due_download_workflows()

        self.assertEqual(_dispatched_run_dates(workflow), [dt.date(2026, 6, 1)])

    def test_catch_up_zero_still_considers_the_newest_month(self, mock_delay, _now):
        workflow = self._workflow(schedule_day_of_month=1, catch_up_days=0)

        run_due_download_workflows()

        self.assertEqual(_dispatched_run_dates(workflow), [dt.date(2026, 7, 1)])


@patch("thredds_ingestion.tasks.process_download_run.delay")
class SeasonalCadenceTests(TestCase):
    def _workflow(self, **overrides):
        defaults = dict(
            cadence=DownloadWorkflow.Cadence.SEASONAL,
            anchor_month=6,  # JJA
            publish_month_offset=3,  # data lands ~September
            schedule_day_of_month=8,
            catch_up_days=2,
        )
        defaults.update(overrides)
        return _workflow(**defaults)

    @patch("thredds_ingestion.tasks.timezone.now", return_value=FIXED_NOW)  # 2026-08-05
    def test_current_year_season_not_attempted_before_its_publish_window(self, _now, mock_delay):
        workflow = self._workflow()

        run_due_download_workflows()

        # JJA 2026 publishes ~2026-09-08; on 2026-08-05 only JJA 2025 is due.
        self.assertEqual(_dispatched_run_dates(workflow), [dt.date(2025, 6, 1)])

    @patch(
        "thredds_ingestion.tasks.timezone.now",
        return_value=dt.datetime(2026, 9, 20, 10, 0, tzinfo=dt_timezone.utc),
    )
    def test_current_year_season_due_inside_its_publish_window(self, _now, mock_delay):
        workflow = self._workflow()

        run_due_download_workflows()

        self.assertEqual(
            _dispatched_run_dates(workflow), [dt.date(2025, 6, 1), dt.date(2026, 6, 1)]
        )

    @patch(
        "thredds_ingestion.tasks.timezone.now",
        return_value=dt.datetime(2026, 3, 10, 10, 0, tzinfo=dt_timezone.utc),
    )
    def test_early_in_year_only_prior_seasons_that_have_happened(self, _now, mock_delay):
        workflow = self._workflow(catch_up_days=3)

        run_due_download_workflows()

        # In March 2026, with catch_up spanning 2026/2025/2024: JJA 2026 hasn't
        # happened yet (gated out); JJA 2025 and JJA 2024 have.
        self.assertEqual(
            _dispatched_run_dates(workflow),
            [dt.date(2024, 6, 1), dt.date(2025, 6, 1)],
        )
