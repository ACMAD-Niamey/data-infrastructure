from django.core.management.base import BaseCommand

from weather_station_ingestion.models import RawPayloadLog
from weather_station_ingestion.services.raw_log_processor import RawLogProcessor

# Map downloaded_content_type fragments to processor method names.
_BUFR_TYPES = {"application/octet-stream", "binary/octet-stream", "bufr"}


class Command(BaseCommand):
    help = "Process downloaded raw logs (text, JSON, BUFR)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        limit = options["limit"]
        processor = RawLogProcessor()

        logs = (
            RawPayloadLog.objects
            .filter(processing_status=RawPayloadLog.ProcessingStatus.DOWNLOADED)
            .order_by("-received_at")[:limit]
        )

        processed = 0

        for log in logs:
            ct = (log.downloaded_content_type or "").lower()

            if any(bt in ct for bt in _BUFR_TYPES) or (log.local_file_path and not log.payload_preview):
                result = processor.process_bufr_file(log)
                method = "bufr"
            elif "json" in ct:
                result = processor.process_json_payload(log)
                method = "json"
            else:
                result = processor.process_text_preview(log)
                method = "text"

            log.processing_status = RawPayloadLog.ProcessingStatus.PROCESSED
            if result:
                log.decision = (
                    f"reprocessed_{method}"
                    f"|parsed={result.parsed_count}"
                    f"|written={result.written_count}"
                    f"|skipped={result.skipped_count}"
                    f"|stations_created={result.created_station_count}"
                    f"|sensors_created={result.created_sensor_count}"
                )
                if result.reason:
                    log.error_message = result.reason
            else:
                log.decision = f"reprocessed_{method}|no_result"

            log.save(update_fields=["processing_status", "decision", "error_message"])
            processed += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} raw logs"))