from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from weather_station_ingestion.models import RawPayloadLog


class Command(BaseCommand):
    help = (
        "Delete downloaded WIS2 files older than a retention window for "
        "safe statuses (processed/skipped/failed)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=None,
            help=(
                "Retention override in days. If omitted, uses "
                "settings.WIS2_DOWNLOAD_RETENTION_DAYS (default 7)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without modifying files or DB rows.",
        )

    def handle(self, *args, **options):
        retention_days = options["older_than_days"]
        if retention_days is None:
            retention_days = int(getattr(settings, "WIS2_DOWNLOAD_RETENTION_DAYS", 7))
        if retention_days <= 0:
            raise CommandError("--older-than-days must be > 0")

        dry_run = bool(options["dry_run"])
        cutoff = timezone.now() - timedelta(days=retention_days)

        safe_statuses = [
            RawPayloadLog.ProcessingStatus.PROCESSED,
            RawPayloadLog.ProcessingStatus.SKIPPED,
            RawPayloadLog.ProcessingStatus.FAILED,
        ]
        logs = (
            RawPayloadLog.objects
            .filter(processing_status__in=safe_statuses, received_at__lte=cutoff)
            .exclude(local_file_path__isnull=True)
            .exclude(local_file_path="")
        )

        scanned = 0
        deleted = 0
        missing = 0
        failed = 0
        nulled = 0
        for log in logs.iterator():
            scanned += 1
            file_path = Path(log.local_file_path)

            if file_path.exists():
                try:
                    if not dry_run:
                        file_path.unlink()
                    deleted += 1
                except Exception:  # noqa: BLE001
                    failed += 1
                    continue
            else:
                missing += 1

            if not dry_run:
                log.local_file_path = None
                log.save(update_fields=["local_file_path"])
            nulled += 1

        mode = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}cutoff={cutoff.isoformat()} scanned={scanned} "
                f"deleted={deleted} missing={missing} failed={failed} "
                f"paths_cleared={nulled}"
            )
        )