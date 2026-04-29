from __future__ import annotations

from django.core.management.base import BaseCommand

from stations.services.country_boundary_sync import CountryBoundarySyncService


class Command(BaseCommand):
    help = "Sync country boundaries from GeoServer WFS into local PostGIS."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Fetch and parse only; do not persist.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        service = CountryBoundarySyncService()
        result = service.sync(persist=not dry_run)
        self.stdout.write(
            self.style.SUCCESS(
                "Country boundary sync complete. "
                f"fetched={result.fetched} upserted={result.upserted} skipped={result.skipped}"
            )
        )
