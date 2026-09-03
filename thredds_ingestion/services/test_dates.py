from datetime import date

from django.test import SimpleTestCase

from thredds_ingestion.services.dates import add_months, clamp_day, month_range


class ClampDayTests(SimpleTestCase):
    def test_day_within_month_is_unchanged(self):
        self.assertEqual(clamp_day(2026, 8, 12), date(2026, 8, 12))

    def test_day_31_in_a_30_day_month(self):
        self.assertEqual(clamp_day(2026, 9, 31), date(2026, 9, 30))

    def test_day_31_in_a_31_day_month_is_kept(self):
        self.assertEqual(clamp_day(2026, 8, 31), date(2026, 8, 31))

    def test_february_non_leap(self):
        self.assertEqual(clamp_day(2026, 2, 30), date(2026, 2, 28))

    def test_february_leap(self):
        self.assertEqual(clamp_day(2024, 2, 30), date(2024, 2, 29))


class AddMonthsTests(SimpleTestCase):
    def test_forward_within_year(self):
        self.assertEqual(add_months(date(2025, 1, 1), 3), date(2025, 4, 1))

    def test_forward_across_year_boundary(self):
        self.assertEqual(add_months(date(2025, 11, 1), 3), date(2026, 2, 1))

    def test_backward_across_year_boundary(self):
        self.assertEqual(add_months(date(2025, 1, 1), -1), date(2024, 12, 1))

    def test_day_component_is_discarded(self):
        self.assertEqual(add_months(date(2025, 6, 17), -1), date(2025, 5, 1))

    def test_zero_delta_normalises_to_first(self):
        self.assertEqual(add_months(date(2025, 6, 30), 0), date(2025, 6, 1))


class MonthRangeTests(SimpleTestCase):
    def test_inclusive_of_both_bounds(self):
        self.assertEqual(
            month_range(date(2025, 1, 1), date(2025, 3, 1)),
            [date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)],
        )

    def test_single_month(self):
        self.assertEqual(month_range(date(2025, 6, 1), date(2025, 6, 1)), [date(2025, 6, 1)])

    def test_bounds_normalised_to_first_of_month(self):
        self.assertEqual(
            month_range(date(2025, 1, 15), date(2025, 2, 2)),
            [date(2025, 1, 1), date(2025, 2, 1)],
        )

    def test_spans_year_boundary(self):
        self.assertEqual(
            month_range(date(2024, 11, 1), date(2025, 2, 1)),
            [date(2024, 11, 1), date(2024, 12, 1), date(2025, 1, 1), date(2025, 2, 1)],
        )
