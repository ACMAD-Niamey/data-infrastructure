from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from weather_station_ingestion.models import RawPayloadLog

#: Rows in a terminal state are safe to drop — matches cleanup_wis2_downloads'
#: precedent. PENDING/DOWNLOADED are excluded by default since they may still
#: be mid-processing; pass --status to override explicitly.
SAFE_STATUSES = [
    RawPayloadLog.ProcessingStatus.PROCESSED,
    RawPayloadLog.ProcessingStatus.SKIPPED,
    RawPayloadLog.ProcessingStatus.FAILED,
]

#: Batched delete size. RawPayloadLog can be large (millions of rows under
#: the global broker's volume) -- a single unbounded DELETE risks a long lock
#: and a big transaction/WAL spike; deleting in slices keeps each individual
#: query small.
DEFAULT_BATCH_SIZE = 5000


class Command(BaseCommand):
    help = (
        "Delete RawPayloadLog rows older than a retention window to reclaim "
        "database space. Unlike cleanup_wis2_downloads (which only deletes "
        "the downloaded files and nulls local_file_path), this deletes the "
        "DB rows themselves -- the actual driver of unbounded table growth "
        "under the WIS2 global broker's message volume."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=None,
            help=(
                "Retention override in days. If omitted, uses "
                "settings.WIS2_RAW_LOG_RETENTION_DAYS (default 7)."
            ),
        )
        parser.add_argument(
            "--status",
            action="append",
            choices=[c.value for c in RawPayloadLog.ProcessingStatus],
            default=None,
            help=(
                "Restrict to this processing_status (repeatable). Default: "
                "processed, skipped, failed (safe/terminal states). Pass "
                "explicitly to also include pending/downloaded."
            ),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help=f"Rows per DELETE batch (default {DEFAULT_BATCH_SIZE}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many rows would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        retention_days = options["older_than_days"]
        if retention_days is None:
            retention_days = int(getattr(settings, "WIS2_RAW_LOG_RETENTION_DAYS", 7))
        if retention_days <= 0:
            raise CommandError("--older-than-days must be > 0")

        batch_size = options["batch_size"]
        if batch_size <= 0:
            raise CommandError("--batch-size must be > 0")

        statuses = options["status"] or [s.value for s in SAFE_STATUSES]
        dry_run = bool(options["dry_run"])
        cutoff = timezone.now() - timedelta(days=retention_days)

        base_qs = RawPayloadLog.objects.filter(
            received_at__lte=cutoff, processing_status__in=statuses
        )

        if dry_run:
            count = base_qs.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY-RUN] cutoff={cutoff.isoformat()} statuses={statuses} "
                    f"would_delete={count}"
                )
            )
            return

        total_deleted = 0
        while True:
            # No OFFSET needed -- each batch's rows are gone by the next
            # iteration, so re-querying the same filter naturally advances.
            batch_ids = list(
                base_qs.order_by("pk").values_list("pk", flat=True)[:batch_size]
            )
            if not batch_ids:
                break
            deleted, _ = RawPayloadLog.objects.filter(pk__in=batch_ids).delete()
            total_deleted += deleted

        self.stdout.write(
            self.style.SUCCESS(
                f"cutoff={cutoff.isoformat()} statuses={statuses} "
                f"deleted={total_deleted}"
            )
        )
        if total_deleted:
            self.stdout.write(
                "Note: DELETE frees space logically; Postgres reclaims the "
                "underlying disk pages via autovacuum (or run "
                "`VACUUM (ANALYZE) raw_payload_logs;` manually for an "
                "immediate, non-exclusive-lock reclaim)."
            )
