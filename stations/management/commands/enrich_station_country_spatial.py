from __future__ import annotations

from django.core.management.base import BaseCommand

from stations.models import Station
from stations.services.country_boundary_sync import CountryBoundarySyncService
from stations.services.station_geography_enricher import StationGeographyEnricher


class Command(BaseCommand):
    help = (
        "Enrich station country_name using GeoServer country boundaries + "
        "spatial join only (no Nominatim fallback)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Max stations to process.")
        parser.add_argument("--dry-run", action="store_true", help="Do not save changes.")
        parser.add_argument(
            "--skip-boundary-sync",
            action="store_true",
            help="Skip fetching/updating country boundaries from GeoServer WFS.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]
        skip_boundary_sync = options["skip_boundary_sync"]

        queryset = Station.objects.order_by("id")
        if limit:
            queryset = queryset[:limit]

        station_ids = list(queryset.values_list("id", flat=True)) if limit else None

        if not skip_boundary_sync:
            sync = CountryBoundarySyncService()
            sync_result = sync.sync(persist=not dry_run)
            self.stdout.write(
                "Boundary sync: "
                f"fetched={sync_result.fetched} upserted={sync_result.upserted} skipped={sync_result.skipped}"
            )

        enricher = StationGeographyEnricher()
        spatial_result = enricher.enrich_country_from_boundaries(
            station_ids=station_ids,
            persist=not dry_run,
            only_missing=True,
        )

        self.stdout.write(
            "Country spatial enrichment: "
            f"candidates={spatial_result['candidates']} updated={spatial_result['updated']}"
        )

