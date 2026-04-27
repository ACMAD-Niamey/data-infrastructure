from __future__ import annotations

import json
import logging

from weather_station_ingestion.models import RawPayloadLog
from weather_station_ingestion.services.payload_classifier import PayloadClassifierFactory
from weather_station_ingestion.services.bufr_parser import BUFRParserService
from weather_station_ingestion.services.json_normalizer import JSONPayloadNormalizationService
from weather_station_ingestion.services.text_normalizer import TextPayloadNormalizationService
from sources.models import DataSource, Dataset, Policy

log = logging.getLogger(__name__)


class RawLogProcessor:
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

        dataset_code = {
            "text_plain": "wis2_text_notifications",
            "json": "wis2_json_observations",
            "bufr": "wis2_bufr_observations",
        }.get(payload_kind, "wis2_text_notifications")

        dataset_name = {
            "wis2_text_notifications": "WIS2 Text Notifications",
            "wis2_json_observations": "WIS2 JSON Observations",
            "wis2_bufr_observations": "WIS2 BUFR Observations",
        }.get(dataset_code, "WIS2 Text Notifications")

        dataset, _ = Dataset.objects.get_or_create(
            dataset_code=dataset_code,
            defaults={
                "source": source,
                "policy": policy,
                "dataset_name": dataset_name,
                "variable_family": "surface_observations",
                "temporal_resolution": "irregular",
                "is_active": True,
            },
        )
        return source, dataset

    def process_text_preview(self, raw_log: RawPayloadLog):
        if not raw_log.payload_preview:
            return None

        source, dataset = self._resolve_source_and_dataset("text_plain")
        normalizer = TextPayloadNormalizationService()

        return normalizer.normalize_and_write(
            text=raw_log.payload_preview,
            dataset=dataset,
            source=source,
            payload_ref=raw_log.source_identifier,
        )

    def process_bufr_file(self, raw_log: RawPayloadLog):
        """Reprocess a BUFR payload from its saved local file path."""
        if not raw_log.local_file_path:
            return None

        import os
        if not os.path.exists(raw_log.local_file_path):
            log.warning("BUFR file missing for log %s: %s", raw_log.pk, raw_log.local_file_path)
            return None

        source, dataset = self._resolve_source_and_dataset("bufr")
        parser = BUFRParserService()

        return parser.parse_and_write(
            file_path=raw_log.local_file_path,
            dataset=dataset,
            source=source,
            payload_ref=raw_log.source_identifier,
        )

    def process_json_payload(self, raw_log: RawPayloadLog):
        if not raw_log.payload_preview:
            return None

        try:
            payload = json.loads(raw_log.payload_preview)
        except (json.JSONDecodeError, TypeError):
            log.warning("Failed to parse JSON for log %s", raw_log.pk)
            return None

        source, dataset = self._resolve_source_and_dataset("json")
        normalizer = JSONPayloadNormalizationService()

        return normalizer.normalize_and_write(
            payload=payload,
            dataset=dataset,
            source=source,
            payload_ref=raw_log.source_identifier,
        )