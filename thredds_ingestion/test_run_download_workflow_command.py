import datetime as dt

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from thredds_ingestion.management.commands.run_download_workflow import Command


class ResolveRunDatesTests(SimpleTestCase):
    def test_single_run_date(self):
        dates = Command._resolve_run_dates({"run_date": "2026-08-05", "run_date_range": None, "days_back": None})
        self.assertEqual(dates, [dt.date(2026, 8, 5)])

    def test_run_date_range_is_inclusive(self):
        dates = Command._resolve_run_dates(
            {"run_date": None, "run_date_range": "2026-08-01:2026-08-03", "days_back": None}
        )
        self.assertEqual(dates, [dt.date(2026, 8, 1), dt.date(2026, 8, 2), dt.date(2026, 8, 3)])

    def test_run_date_range_end_before_start_raises(self):
        with self.assertRaises(CommandError):
            Command._resolve_run_dates(
                {"run_date": None, "run_date_range": "2026-08-05:2026-08-01", "days_back": None}
            )

    def test_run_date_range_missing_colon_raises(self):
        with self.assertRaises(CommandError):
            Command._resolve_run_dates({"run_date": None, "run_date_range": "2026-08-05", "days_back": None})

    def test_days_back_ends_on_today_inclusive(self):
        dates = Command._resolve_run_dates({"run_date": None, "run_date_range": None, "days_back": 3})
        today = dt.date.today()
        self.assertEqual(dates, [today - dt.timedelta(days=2), today - dt.timedelta(days=1), today])

    def test_days_back_zero_raises(self):
        with self.assertRaises(CommandError):
            Command._resolve_run_dates({"run_date": None, "run_date_range": None, "days_back": 0})
