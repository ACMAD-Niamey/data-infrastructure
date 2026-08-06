from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import TestCase

from thredds_ingestion.services.ingest_bridge import push_to_ingest

VALID_DT = datetime(2026, 8, 6, tzinfo=timezone.utc)
VALID_END_DT = datetime(2026, 8, 11, tzinfo=timezone.utc)


def _dataset(dataset_id="5daymean", cadence="daily"):
    ds = MagicMock()
    ds.dataset_id = dataset_id
    ds.cadence = cadence
    return ds


class PushToIngestPayloadTests(TestCase):
    @patch("ingest.tasks.process_ingestion_run")
    def test_point_in_time_uses_single_datetime_field(self, mock_process):
        run = push_to_ingest(
            dataset=_dataset(), href="s3://geodata/x.tif", item_id="x_20260806", valid_datetime=VALID_DT
        )

        self.assertEqual(run.payload["datetime"], VALID_DT.isoformat())
        self.assertNotIn("start_datetime", run.payload)
        self.assertNotIn("end_datetime", run.payload)

    @patch("ingest.tasks.process_ingestion_run")
    def test_window_uses_start_and_end_datetime_fields(self, mock_process):
        run = push_to_ingest(
            dataset=_dataset(),
            href="s3://geodata/x.tif",
            item_id="x_20260806",
            valid_datetime=VALID_DT,
            valid_end_datetime=VALID_END_DT,
        )

        self.assertEqual(run.payload["start_datetime"], VALID_DT.isoformat())
        self.assertEqual(run.payload["end_datetime"], VALID_END_DT.isoformat())
        self.assertNotIn("datetime", run.payload)
