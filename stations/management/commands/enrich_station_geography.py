from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from stations.models import Station
from stations.services.country_boundary_sync import CountryBoundarySyncService
from stations.services.station_geography_enricher import StationGeographyEnricher


class Command(BaseCommand):
    help = "Backfill station country/admin geography fields."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Max stations to process.")
        parser.add_argument("--dry-run", action="store_true", help="Do not save changes.")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="How often to print progress (number of stations).",
        )
        parser.add_argument(
            "--skip-boundary-sync",
            action="store_true",
            help="Skip fetching/updating country boundaries from GeoServer WFS.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]
        batch_size = max(1, int(options["batch_size"]))
        skip_boundary_sync = options["skip_boundary_sync"]

        queryset = Station.objects.order_by("id")
        if limit:
            queryset = queryset[:limit]

        station_ids = list(queryset.values_list("id", flat=True))

        if not skip_boundary_sync:
            sync = CountryBoundarySyncService()
            sync_result = sync.sync(persist=not dry_run)
            self.stdout.write(
                "Boundary sync: "
                f"fetched={sync_result.fetched} upserted={sync_result.upserted} skipped={sync_result.skipped}"
            )

        enricher = StationGeographyEnricher()
        spatial_result = enricher.enrich_country_from_boundaries(
            station_ids=station_ids if limit else None,
            persist=not dry_run,
            only_missing=True,
        )
        self.stdout.write(
            "Country spatial enrichment: "
            f"candidates={spatial_result['candidates']} updated={spatial_result['updated']}"
        )

        fallback_queryset = Station.objects.order_by("id").filter(
            Q(country_name__isnull=True)
            | Q(country_name__exact="")
            | Q(canonical_code__isnull=True)
            | Q(canonical_code__exact="")
        )
        if limit:
            fallback_queryset = fallback_queryset.filter(id__in=station_ids)

        processed = 0
        updated = 0

        self.stdout.write(
            f"Starting enrichment dry_run={dry_run} limit={limit or 'all'} batch_size={batch_size}"
        )
        for station in fallback_queryset:
            processed += 1
            before = (station.canonical_code, station.country_name, station.admin1, station.admin2)
            result = enricher.enrich_station_geography(station, persist=not dry_run)

            after = (
                result.get("canonical_code"),
                result.get("country_name"),
                result.get("admin1"),
                result.get("admin2"),
            )
            if after != before:
                updated += 1

            if processed % batch_size == 0:
                self.stdout.write(
                    f"Progress: processed={processed} updated={updated} unchanged={processed - updated}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"spatial_updated={spatial_result['updated']} "
                f"fallback_processed={processed} fallback_updated={updated} "
                f"fallback_unchanged={processed - updated}"
            )
        )

