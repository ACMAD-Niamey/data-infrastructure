from __future__ import annotations

import json
import logging

from django.conf import settings
from django.db import close_old_connections

from weather_station_ingestion.models import RawPayloadLog
from weather_station_ingestion.services.africa_filter import AfricaFilterService
from weather_station_ingestion.services.mqtt_client import MQTTClientFactory
from weather_station_ingestion.services.payload_classifier import PayloadClassifierFactory
from weather_station_ingestion.services.text_normalizer import TextPayloadNormalizationService
from weather_station_ingestion.services.wis2_downloader import WIS2Downloader
from weather_station_ingestion.services.wis2_parser import WIS2NotificationParser
from sources.models import DataSource, Dataset, Policy
from weather_station_ingestion.services.json_normalizer import JSONPayloadNormalizationService
from weather_station_ingestion.services.bufr_parser import BUFRParserService

log = logging.getLogger(__name__)


class WIS2Consumer:
    def __init__(self) -> None:
        self.parser = WIS2NotificationParser()
        self.downloader = WIS2Downloader()
        self.africa_filter = AfricaFilterService()
        self.text_normalizer = TextPayloadNormalizationService()
        self.json_normalizer = JSONPayloadNormalizationService()
        self.bufr_parser = BUFRParserService()

        self.client = MQTTClientFactory().build(
            self.on_connect,
            self.on_message,
            self.on_disconnect,
        )

    def connect(self) -> None:
        self.client.connect(
            settings.WIS2_BROKER_HOST,
            settings.WIS2_BROKER_PORT,
            60,
        )

    def loop_forever(self) -> None:
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        log.info("Connected to WIS2 broker with reason code %s", reason_code)
        for topic, qos in settings.WIS2_TOPICS:
            client.subscribe(topic, qos=qos)
            log.info("Subscribed to topic %s", topic)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        log.warning("Disconnected from WIS2 broker: %s", reason_code)

    def _resolve_source_and_dataset(self, payload_kind: str = "text_plain") -> tuple[DataSource, Dataset]:
        source, _ = DataSource.objects.get_or_create(
            source_code="wis2-global-broker",
            defaults={
                "source_name": "WIS2 Global Broker",
                "source_type": "wis2",
                "protocol": "mqtt",
                "is_active": True,
            },
        )

        policy, _ = Policy.objects.get_or_create(
            name="Internal Only",
            defaults={
                "owner_org": "Internal",
                "public_api_allowed": False,
                "dashboard_allowed": False,
                "internal_allowed": True,
                "partner_allowed": False,
                "raw_download_allowed": False,
                "aggregate_allowed": True,
                "station_visible": True,
            },
        )

        dataset_map = {
            "text_plain": ("wis2_text_notifications", "WIS2 Text Notifications"),
            "json": ("wis2_json_observations", "WIS2 JSON Observations"),
            "bufr": ("wis2_bufr_observations", "WIS2 BUFR Observations"),
        }
        code, name = dataset_map.get(payload_kind, ("wis2_text_notifications", "WIS2 Text Notifications"))

        dataset, _ = Dataset.objects.get_or_create(
            dataset_code=code,
            defaults={
                "source": source,
                "policy": policy,
                "dataset_name": name,
                "variable_family": "surface_observations",
                "temporal_resolution": "irregular",
                "is_active": True,
            },
        )
        return source, dataset

    def on_message(self, client, userdata, msg):
        close_old_connections()

        try:
            payload_json = json.loads(msg.payload.decode("utf-8", errors="replace"))
            notification = self.parser.parse(msg.topic, payload_json)

            raw_log = RawPayloadLog.objects.create(
                source_type=RawPayloadLog.SourceType.WIS2,
                source_identifier=notification.source_identifier,
                topic=notification.topic,
                data_id=notification.data_id,
                metadata_id=notification.metadata_id,
                canonical_url=notification.canonical_url,
                content_type=notification.content_type,
                pubtime=notification.pubtime,
                data_datetime=notification.data_datetime,
                global_cache=notification.global_cache,
                payload=notification.raw_payload if settings.WIS2_STORE_FULL_PAYLOAD else None,
                processing_status=RawPayloadLog.ProcessingStatus.PENDING,
                decision="candidate",
            )

            if settings.WIS2_ONLY_CACHE_TOPICS and not notification.topic.startswith("cache/"):
                raw_log.processing_status = RawPayloadLog.ProcessingStatus.SKIPPED
                raw_log.decision = "skipped_non_cache_topic"
                raw_log.save(update_fields=["processing_status", "decision"])
                return

            if not notification.canonical_url:
                raw_log.processing_status = RawPayloadLog.ProcessingStatus.SKIPPED
                raw_log.decision = "skipped_missing_canonical_url"
                raw_log.save(update_fields=["processing_status", "decision"])
                return

            download_result = self.downloader.download(notification.canonical_url)

            classification = PayloadClassifierFactory.classify(
                notification.content_type,
                download_result.content_type,
                download_result.content,
            )

            preview = None
            if classification.payload_kind in {"text_plain", "json"} and settings.WIS2_STORE_TEXT_PREVIEW:
                preview = download_result.content.decode("utf-8", errors="replace")[
                    : settings.WIS2_MAX_PAYLOAD_PREVIEW_CHARS
                ]

            africa_result = self.africa_filter.from_topic(notification.topic)

            raw_log.payload_size_bytes = download_result.content_length
            raw_log.downloaded_content_type = download_result.content_type
            raw_log.local_file_path = download_result.local_file_path
            raw_log.payload_preview = preview
            raw_log.processing_status = RawPayloadLog.ProcessingStatus.DOWNLOADED
            raw_log.decision = f"{classification.payload_kind}|{africa_result.reason}"
            raw_log.error_message = None if classification.is_supported else classification.notes
            raw_log.save(
                update_fields=[
                    "payload_size_bytes",
                    "downloaded_content_type",
                    "local_file_path",
                    "payload_preview",
                    "processing_status",
                    "decision",
                    "error_message",
                ]
            )

            if classification.payload_kind not in {"text_plain", "json", "bufr"}:
                raw_log.processing_status = RawPayloadLog.ProcessingStatus.SKIPPED
                raw_log.decision = f"skipped_unsupported|kind={classification.payload_kind}"
                raw_log.save(update_fields=["processing_status", "decision"])
                return

            source, dataset = self._resolve_source_and_dataset(classification.payload_kind)

            if classification.payload_kind == "text_plain":
                text_content = download_result.content.decode("utf-8", errors="replace")
                norm_result = self.text_normalizer.normalize_and_write(
                    text=text_content,
                    dataset=dataset,
                    source=source,
                    payload_ref=raw_log.source_identifier,
                )

                raw_log.processing_status = RawPayloadLog.ProcessingStatus.PROCESSED
                raw_log.decision = (
                    f"text_normalized|parsed={norm_result.parsed_count}"
                    f"|written={norm_result.written_count}"
                    f"|skipped={norm_result.skipped_count}"
                    f"|stations_created={norm_result.created_station_count}"
                    f"|sensors_created={norm_result.created_sensor_count}"
                )
                if norm_result.reason:
                    raw_log.error_message = norm_result.reason

                raw_log.save(update_fields=["processing_status", "decision", "error_message"])
                return

            if classification.payload_kind == "json":
                try:
                    json_content = download_result.content.decode("utf-8", errors="replace")
                    json_payload = json.loads(json_content)
                except Exception:
                    raw_log.processing_status = RawPayloadLog.ProcessingStatus.FAILED
                    raw_log.decision = "json_parse_failed"
                    raw_log.error_message = "Downloaded payload classified as JSON but could not be decoded."
                    raw_log.save(update_fields=["processing_status", "decision", "error_message"])
                    return

                norm_result = self.json_normalizer.normalize_and_write(
                    payload=json_payload,
                    dataset=dataset,
                    source=source,
                    payload_ref=raw_log.source_identifier,
                )

                raw_log.processing_status = RawPayloadLog.ProcessingStatus.PROCESSED
                raw_log.decision = (
                    f"json_normalized|parsed={norm_result.parsed_count}"
                    f"|written={norm_result.written_count}"
                    f"|skipped={norm_result.skipped_count}"
                    f"|stations_created={norm_result.created_station_count}"
                    f"|sensors_created={norm_result.created_sensor_count}"
                )
                if norm_result.reason:
                    raw_log.error_message = norm_result.reason

                raw_log.save(update_fields=["processing_status", "decision", "error_message"])
                return

            if classification.payload_kind == "bufr":
                file_path = download_result.local_file_path
                if not file_path:
                    raw_log.processing_status = RawPayloadLog.ProcessingStatus.FAILED
                    raw_log.error_message = "BUFR payload not saved to disk for parsing."
                    raw_log.save(update_fields=["processing_status", "error_message"])
                    return

                norm_result = self.bufr_parser.parse_and_write(
                    file_path=file_path,
                    dataset=dataset,
                    source=source,
                    payload_ref=raw_log.source_identifier,
                )

                raw_log.processing_status = RawPayloadLog.ProcessingStatus.PROCESSED
                raw_log.decision = (
                    f"bufr_normalized|parsed={norm_result.parsed_count}"
                    f"|written={norm_result.written_count}"
                    f"|skipped={norm_result.skipped_count}"
                    f"|stations_created={norm_result.created_station_count}"
                    f"|sensors_created={norm_result.created_sensor_count}"
                )
                if norm_result.reason:
                    raw_log.error_message = norm_result.reason

                raw_log.save(update_fields=["processing_status", "decision", "error_message"])
                return

        except Exception as exc:
            log.exception("Failed to process MQTT message")
            RawPayloadLog.objects.create(
                source_type=RawPayloadLog.SourceType.WIS2,
                topic=msg.topic,
                processing_status=RawPayloadLog.ProcessingStatus.FAILED,
                decision="consumer_failed",
                error_message=str(exc),
            )