from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase

from thredds_ingestion.services.ingest_bridge import build_minio_key, push_to_ingest

VALID_DT = datetime(2026, 8, 6, tzinfo=timezone.utc)
VALID_END_DT = datetime(2026, 8, 11, tzinfo=timezone.utc)


class PushToIngestPayloadTests(TestCase):
    @patch("ingest.tasks.process_ingestion_run")
    def test_point_in_time_uses_single_datetime_field(self, mock_process):
        run = push_to_ingest(
            collection="5daymean",
            cadence="daily",
            href="s3://geodata/x.tif",
            item_id="x_20260806",
            valid_datetime=VALID_DT,
        )

        self.assertEqual(run.payload["datetime"], VALID_DT.isoformat())
        self.assertNotIn("start_datetime", run.payload)
        self.assertNotIn("end_datetime", run.payload)

    @patch("ingest.tasks.process_ingestion_run")
    def test_window_uses_start_and_end_datetime_fields(self, mock_process):
        run = push_to_ingest(
            collection="5daymean",
            cadence="dekadal",
            href="s3://geodata/x.tif",
            item_id="x_20260806",
            valid_datetime=VALID_DT,
            valid_end_datetime=VALID_END_DT,
        )

        self.assertEqual(run.payload["start_datetime"], VALID_DT.isoformat())
        self.assertEqual(run.payload["end_datetime"], VALID_END_DT.isoformat())
        self.assertNotIn("datetime", run.payload)

    @patch("ingest.tasks.process_ingestion_run")
    def test_ingestion_run_carries_the_resolved_collection_not_a_dataset_id(self, mock_process):
        run = push_to_ingest(
            collection="precipitation-tercile-cpc-uni",
            cadence="monthly",
            href="s3://geodata/x.tif",
            item_id="precipitation-tercile-cpc-uni_20250901",
            valid_datetime=VALID_DT,
        )

        self.assertEqual(run.dataset_id, "precipitation-tercile-cpc-uni")
        self.assertEqual(run.cadence, "monthly")


class BuildMinioKeyTests(TestCase):
    def test_key_is_prefixed_by_collection(self):
        from datetime import date

        key = build_minio_key("precipitation-tercile-rfe2", date(2025, 9, 1), "AFR_Sep_2025_RFE2_Tercile.tif")

        self.assertEqual(
            key, "precipitation-tercile-rfe2/2025/09/AFR_Sep_2025_RFE2_Tercile.tif"
        )
