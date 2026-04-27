from django.core.management.base import BaseCommand

from observations.services.observation_reader import ObservationReader


class Command(BaseCommand):
    help = "Show latest normalized observations"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        limit = options["limit"]
        records = ObservationReader().latest(limit=limit)

        if not records:
            self.stdout.write(self.style.WARNING("No observations found."))
            return

        for row in records:
            self.stdout.write(
                f"station_id={row.station_id} "
                f"time={row.observed_at} "
                f"var={row.variable_code} "
                f"value={row.cleaned_value} "
                f"unit={row.unit} "
                f"qc={row.qc_flag}"
            )