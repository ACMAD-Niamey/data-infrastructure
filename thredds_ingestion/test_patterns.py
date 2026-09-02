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


def _workflow(
    base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/forecastinservice/ensemble5",
    folder_pattern="{run_date:%Y%m%d}",
):
    wf = MagicMock()
    wf.source_base_url = base_url
    wf.folder_pattern = folder_pattern
    return wf


def _workflow_file(
    filename_pattern, *, lead_hours_csv="", threshold_label="", item_id_pattern="", validity_hours=None
):
    wff = MagicMock()
    wff.filename_pattern = filename_pattern
    wff.lead_hours_csv = lead_hours_csv
    wff.threshold_label = threshold_label
    wff.item_id_pattern = item_id_pattern
    wff.validity_hours = validity_hours
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

    def test_valid_date_placeholder_for_day_granularity_products(self):
        # heat_index_20260806_20260809.tif: second date is run_date + lead
        # days, not a bare hour count - matches the real
        # F_24hrPrecip_{run_date}_{valid_date}.nc shape found on THREDDS.
        workflow = _workflow()
        wff = _workflow_file(
            "heat_index_{run_date:%Y%m%d}_{valid_date:%Y%m%d}.tif", lead_hours_csv="0,24,48,72"
        )

        _, filename_0 = render_source_url(workflow, wff, RUN_DATE, 0)
        _, filename_3d = render_source_url(workflow, wff, RUN_DATE, 72)

        self.assertEqual(filename_0, "heat_index_20260805_20260805.tif")
        self.assertEqual(filename_3d, "heat_index_20260805_20260808.tif")

    def test_valid_date_defaults_to_run_date_with_no_lead_hours(self):
        workflow = _workflow()
        wff = _workflow_file("5daymean_{run_date:%Y%m%d}_{valid_date:%Y%m%d}.tif")

        _, filename = render_source_url(workflow, wff, RUN_DATE, None)

        self.assertEqual(filename, "5daymean_20260805_20260805.tif")

    def test_real_lead_hours_zero_is_distinct_from_sentinel(self):
        # A pattern that references bare {lead_hours} must render "0" for a
        # real, configured lead_hours=0 (e.g. a "day 0" forecast in an
        # explicit "0,24,48" series) - it must not be silently dropped the
        # way an unconfigured/sentinel lead_hours is.
        workflow = _workflow()
        wff = _workflow_file("mix{run_date:%Y%m%d}_{lead_hours}.tif", lead_hours_csv="0,24")

        _, filename = render_source_url(workflow, wff, RUN_DATE, 0)

        self.assertEqual(filename, "mix20260805_0.tif")


class ValidEndDatePlaceholderTests(SimpleTestCase):
    """{valid_end_date}: needed for products whose filename embeds a date
    *range* rather than a single date, e.g. the real
    Vigilance_Data_GEFS_Week_1_Init-20260810_Valid-20260811-20260817.csv
    shape found on THREDDS (a 7-day window starting the day after run_date)."""

    def test_valid_end_date_is_start_plus_validity_hours(self):
        workflow = _workflow()
        wff = _workflow_file(
            "Vigilance_Data_GEFS_Week_1_Init-{run_date:%Y%m%d}_Valid-{valid_date:%Y%m%d}-{valid_end_date:%Y%m%d}.csv",
            lead_hours_csv="24,192",
            validity_hours=144,
        )

        _, filename = render_source_url(workflow, wff, RUN_DATE, 24)

        self.assertEqual(
            filename,
            "Vigilance_Data_GEFS_Week_1_Init-20260805_Valid-20260806-20260812.csv",
        )

    def test_missing_validity_hours_raises_loudly(self):
        # Misconfiguration: pattern references {valid_end_date} but the
        # mapping has no validity_hours configured.
        workflow = _workflow()
        wff = _workflow_file("mix{run_date:%Y%m%d}_{valid_end_date:%Y%m%d}.tif")

        with self.assertRaises(PatternRenderError):
            render_source_url(workflow, wff, RUN_DATE, None)


class MonthTokenTests(SimpleTestCase):
    """{month_abbr}/{month_name} for monthly products whose THREDDS path
    embeds the English month literally, e.g.
    .../monthly/Sep/tif/AFR_Sep_2025_RFE2_Precip-Anom.tif."""

    def test_month_abbr_in_folder_and_filename(self):
        workflow = _workflow(
            base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/CDD/ClimateBulletin_TN/OBS_RAIN_ANOM/monthly",
            folder_pattern="{month_abbr}/tif",
        )
        wff = _workflow_file("AFR_{month_abbr}_{run_date:%Y}_RFE2_Precip-Anom.tif")

        url, filename = render_source_url(workflow, wff, date(2025, 9, 1), None)

        self.assertEqual(filename, "AFR_Sep_2025_RFE2_Precip-Anom.tif")
        self.assertTrue(url.endswith("/OBS_RAIN_ANOM/monthly/Sep/tif/AFR_Sep_2025_RFE2_Precip-Anom.tif"))

    def test_month_tokens_are_english_regardless_of_run_date_month(self):
        workflow = _workflow(folder_pattern="{month_name}")
        wff = _workflow_file("{month_abbr}.tif")

        for month, abbr, name in [
            (1, "Jan", "January"), (5, "May", "May"), (10, "Oct", "October"), (12, "Dec", "December")
        ]:
            _, filename = render_source_url(workflow, wff, date(2024, month, 1), None)
            self.assertEqual(filename, f"{abbr}.tif")

    def test_literal_season_folder_passes_through_untouched(self):
        # Seasonal products: the season (JJA = Jun/Jul/Aug) isn't derivable
        # from a date, so the folder is a literal with no placeholders.
        workflow = _workflow(
            base_url="https://sgbd.acmad.org/thredds/fileServer/ACMAD/CDD/ClimateBulletin_TN/OBS_RAIN_ANOM/seasonal",
            folder_pattern="JJA/tif",
        )
        wff = _workflow_file("AFR_JJA_{run_date:%Y}_RFE2_Precip-Anom.tif")

        url, filename = render_source_url(workflow, wff, date(2025, 6, 1), None)

        self.assertEqual(filename, "AFR_JJA_2025_RFE2_Precip-Anom.tif")
        self.assertTrue(url.endswith("/seasonal/JJA/tif/AFR_JJA_2025_RFE2_Precip-Anom.tif"))


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

    def test_real_lead_hours_zero_gets_hour_suffix_like_any_other_lead(self):
        wff = _workflow_file("mix{run_date:%Y%m%d}_{lead_hours}.tif", lead_hours_csv="0,24")

        item_id = render_item_id(wff, "mix6", RUN_DATE, 0)

        self.assertEqual(item_id, "mix6_20260805_0h")

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
