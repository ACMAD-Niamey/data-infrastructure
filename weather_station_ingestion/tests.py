import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from weather_station_ingestion.models import RawPayloadLog
from weather_station_ingestion.services.wis2_consumer import WIS2Consumer


def _make_log(*, status, days_old, **extra):
    """Create a RawPayloadLog and backdate received_at (auto_now_add bypass)."""
    log = RawPayloadLog.objects.create(processing_status=status, **extra)
    RawPayloadLog.objects.filter(pk=log.pk).update(
        received_at=timezone.now() - timedelta(days=days_old)
    )
    log.refresh_from_db()
    return log


# ---------------------------------------------------------------------------
# prune_wis2_raw_logs
# ---------------------------------------------------------------------------


class PruneWis2RawLogsCommandTests(TestCase):
    def test_deletes_only_safe_statuses_past_retention(self):
        old_processed = _make_log(status=RawPayloadLog.ProcessingStatus.PROCESSED, days_old=10)
        old_skipped = _make_log(status=RawPayloadLog.ProcessingStatus.SKIPPED, days_old=10)
        old_pending = _make_log(status=RawPayloadLog.ProcessingStatus.PENDING, days_old=10)
        recent_processed = _make_log(status=RawPayloadLog.ProcessingStatus.PROCESSED, days_old=1)

        call_command("prune_wis2_raw_logs", "--older-than-days", "7")

        remaining = set(RawPayloadLog.objects.values_list("pk", flat=True))
        self.assertNotIn(old_processed.pk, remaining)
        self.assertNotIn(old_skipped.pk, remaining)
        # pending is excluded by default (not a "safe" terminal status)
        self.assertIn(old_pending.pk, remaining)
        # not past retention yet
        self.assertIn(recent_processed.pk, remaining)

    def test_dry_run_deletes_nothing(self):
        old_processed = _make_log(status=RawPayloadLog.ProcessingStatus.PROCESSED, days_old=10)

        call_command("prune_wis2_raw_logs", "--older-than-days", "7", "--dry-run")

        self.assertTrue(RawPayloadLog.objects.filter(pk=old_processed.pk).exists())

    def test_status_override_can_include_pending(self):
        old_pending = _make_log(status=RawPayloadLog.ProcessingStatus.PENDING, days_old=10)

        call_command(
            "prune_wis2_raw_logs", "--older-than-days", "7", "--status", "pending"
        )

        self.assertFalse(RawPayloadLog.objects.filter(pk=old_pending.pk).exists())

    def test_batch_size_deletes_all_matching_rows_across_batches(self):
        for _ in range(7):
            _make_log(status=RawPayloadLog.ProcessingStatus.SKIPPED, days_old=10)

        call_command(
            "prune_wis2_raw_logs", "--older-than-days", "7", "--batch-size", "2"
        )

        self.assertEqual(RawPayloadLog.objects.count(), 0)

    @override_settings(WIS2_RAW_LOG_RETENTION_DAYS=3)
    def test_uses_settings_default_when_flag_omitted(self):
        just_past = _make_log(status=RawPayloadLog.ProcessingStatus.FAILED, days_old=4)
        just_before = _make_log(status=RawPayloadLog.ProcessingStatus.FAILED, days_old=2)

        call_command("prune_wis2_raw_logs")

        self.assertFalse(RawPayloadLog.objects.filter(pk=just_past.pk).exists())
        self.assertTrue(RawPayloadLog.objects.filter(pk=just_before.pk).exists())


# ---------------------------------------------------------------------------
# WIS2_DOWNLOAD_ENABLED master switch
# ---------------------------------------------------------------------------


def _cache_notification(canonical_url="https://example.org/data/file.bin"):
    payload = {
        "id": "test-msg-1",
        "properties": {},
        "links": [{"rel": "canonical", "href": canonical_url, "type": "application/octet-stream"}],
    }
    msg = MagicMock()
    msg.topic = "cache/a/wis2/test"
    msg.payload.decode.return_value = json.dumps(payload)
    return msg


class WIS2DownloadEnabledSwitchTests(TestCase):
    # on_message() calls close_old_connections() as it would in the real
    # long-running consumer loop -- fine there, but it tears down TestCase's
    # wrapping transaction/connection here, so it's a no-op for these tests.
    @patch("weather_station_ingestion.services.wis2_consumer.close_old_connections")
    @override_settings(WIS2_DOWNLOAD_ENABLED=False)
    @patch("weather_station_ingestion.services.wis2_consumer.WIS2Downloader")
    @patch("weather_station_ingestion.services.wis2_consumer.MQTTClientFactory")
    def test_download_disabled_skips_fetch_but_logs_notification(
        self, _mock_factory, mock_downloader_cls, _mock_close_conns
    ):
        mock_downloader = MagicMock()
        mock_downloader_cls.return_value = mock_downloader

        consumer = WIS2Consumer()
        consumer.on_message(client=MagicMock(), userdata=None, msg=_cache_notification())

        mock_downloader.download.assert_not_called()
        log = RawPayloadLog.objects.get()
        self.assertEqual(log.processing_status, RawPayloadLog.ProcessingStatus.SKIPPED)
        self.assertEqual(log.decision, "skipped_downloads_disabled")

    @patch("weather_station_ingestion.services.wis2_consumer.close_old_connections")
    @override_settings(WIS2_DOWNLOAD_ENABLED=True)
    @patch("weather_station_ingestion.services.wis2_consumer.PayloadClassifierFactory")
    @patch("weather_station_ingestion.services.wis2_consumer.WIS2Downloader")
    @patch("weather_station_ingestion.services.wis2_consumer.MQTTClientFactory")
    def test_download_enabled_still_fetches(
        self, _mock_factory, mock_downloader_cls, mock_classifier, _mock_close_conns
    ):
        mock_downloader = MagicMock()
        mock_downloader.download.return_value = MagicMock(
            content=b"x", content_type="application/octet-stream",
            content_length=1, local_file_path=None,
        )
        mock_downloader_cls.return_value = mock_downloader
        mock_classifier.classify.return_value = MagicMock(
            payload_kind="unsupported", is_supported=False, notes=""
        )

        consumer = WIS2Consumer()
        consumer.on_message(client=MagicMock(), userdata=None, msg=_cache_notification())

        mock_downloader.download.assert_called_once()
