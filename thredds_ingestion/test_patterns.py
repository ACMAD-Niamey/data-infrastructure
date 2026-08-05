from datetime import date, datetime, timezone
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from thredds_ingestion.services.patterns import (
    PatternRenderError,
    render_item_id,
    render_source_url,
    render_valid_datetime,
)

RUN_DATE = date(2026, 8, 5)


def _workflow(base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5"):
    wf = MagicMock()
    wf.source_base_url = base_url
    wf.folder_pattern = "{run_date:%Y%m%d}"
    return wf


def _workflow_file(filename_pattern, *, lead_hours_csv="", threshold_label="", item_id_pattern=""):
    wff = MagicMock()
    wff.filename_pattern = filename_pattern
    wff.lead_hours_csv = lead_hours_csv
    wff.threshold_label = threshold_label
    wff.item_id_pattern = item_id_pattern
    return wff


class RenderSourceUrlTests(SimpleTestCase):
    def test_lead_hour_products_render_distinct_filenames_per_lead_hour(self):
        workflow = _workflow()
        wff = _workflow_file("mix{run_date:%Y%m%d}_{lead_hours}.tif", lead_hours_csv="24,96")

        url_24, name_24 = render_source_url(workflow, wff, RUN_DATE, 24)
        url_96, name_96 = render_source_url(workflow, wff, RUN_DATE, 96)

        self.assertEqual(name_24, "mix20260805_24.tif")
        self.assertEqual(name_96, "mix20260805_96.tif")
        self.assertNotEqual(url_24, url_96)
        self.assertTrue(url_24.endswith("/20260805/mix20260805_24.tif"))

    def test_single_file_per_day_product_renders_once_with_no_lead_hours(self):
        workflow = _workflow()
        wff = _workflow_file("5daymean_{run_date:%Y%m%d}.tif")

        url, filename = render_source_url(workflow, wff, RUN_DATE, None)

        self.assertEqual(filename, "5daymean_20260805.tif")
        self.assertTrue(url.endswith("/20260805/5daymean_20260805.tif"))

    def test_threshold_literal_is_substituted(self):
        workflow = _workflow()
        wff = _workflow_file(
            "pop{run_date:%Y%m%d}_{threshold}_{lead_hours}.tif",
            lead_hours_csv="24",
            threshold_label="50mm",
        )

        _, filename = render_source_url(workflow, wff, RUN_DATE, 24)

        self.assertEqual(filename, "pop20260805_50mm_24.tif")

    def test_missing_lead_hours_placeholder_raises_loudly(self):
        # Misconfiguration: pattern references {lead_hours} but the mapping
        # has none configured (lead_hours=None omits it from context).
        workflow = _workflow()
        wff = _workflow_file("mix{run_date:%Y%m%d}_{lead_hours}.tif")

        with self.assertRaises(PatternRenderError):
            render_source_url(workflow, wff, RUN_DATE, None)


class RenderItemIdTests(SimpleTestCase):
    def test_item_id_differs_across_lead_hours(self):
        wff = _workflow_file("mix{run_date:%Y%m%d}_{lead_hours}.tif", lead_hours_csv="24,96")

        id_24 = render_item_id(wff, "mix6", RUN_DATE, 24)
        id_96 = render_item_id(wff, "mix6", RUN_DATE, 96)

        self.assertNotEqual(id_24, id_96)
        self.assertEqual(id_24, "mix6_20260805_24h")

    def test_no_lead_hours_item_id_has_no_hour_suffix(self):
        wff = _workflow_file("5daymean_{run_date:%Y%m%d}.tif")

        item_id = render_item_id(wff, "5daymean", RUN_DATE, None)

        self.assertEqual(item_id, "5daymean_20260805")

    def test_explicit_item_id_pattern_is_used_when_set(self):
        wff = _workflow_file(
            "pop{run_date:%Y%m%d}_{threshold}_{lead_hours}.tif",
            lead_hours_csv="24",
            threshold_label="50mm",
            item_id_pattern="wwfd_pop_50mm_{run_date:%Y%m%d}_{lead_hours}",
        )

        item_id = render_item_id(wff, "wwfd_pop_50mm", RUN_DATE, 24)

        self.assertEqual(item_id, "wwfd_pop_50mm_20260805_24")


class RenderValidDatetimeTests(SimpleTestCase):
    def test_lead_hours_added_to_run_date_midnight_utc(self):
        result = render_valid_datetime(RUN_DATE, 24)
        self.assertEqual(result, datetime(2026, 8, 6, 0, 0, tzinfo=timezone.utc))

    def test_no_lead_hours_is_run_date_midnight_utc(self):
        result = render_valid_datetime(RUN_DATE, None)
        self.assertEqual(result, datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc))
