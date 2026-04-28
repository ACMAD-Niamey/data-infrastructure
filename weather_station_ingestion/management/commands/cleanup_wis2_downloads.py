from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from weather_station_ingestion.models import RawPayloadLog


class Command(BaseCommand):
    help = "Delete downloaded WIS2 files for processed or skipped logs"

    def handle(self, *args, **options):
        count = 0

        logs = RawPayloadLog.objects.exclude(local_file_path__isnull=True).exclude(local_file_path="")
        for log in logs.iterator():
            file_path = Path(log.local_file_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                    count += 1
                except Exception:
                    continue

            log.local_file_path = None
            log.save(update_fields=["local_file_path"])

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} downloaded files"))