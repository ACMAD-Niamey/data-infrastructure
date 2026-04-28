"""Management command: import_wmo_stations

Downloads the NOAA ISD station history CSV and upserts WMO surface stations
into the local ``stations`` table.

Usage
-----
.. code-block:: bash

    # Import all African stations (default)
    python manage.py import_wmo_stations

    # Dry-run: parse and count without writing
    python manage.py import_wmo_stations --dry-run

    # Import only the first 20 rows (for smoke-testing)
    python manage.py import_wmo_stations --limit 20

    # Import global stations (skips Africa-only filter)
    python manage.py import_wmo_stations --no-africa-only

Notes
-----
- Idempotent: safe to run multiple times; existing stations are updated only
  when blank fields can be filled in.
- The source CSV URL can be overridden with ``--source-url``.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from stations.services.isd_station_importer import ISD_CSV_URL, ISDStationImporter


class Command(BaseCommand):
    help = "Import WMO surface stations from the NOAA ISD station history CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-url",
            default=ISD_CSV_URL,
            help="URL of the ISD station history CSV (default: NOAA public endpoint).",
        )
        parser.add_argument(
            "--no-africa-only",
            action="store_true",
            default=False,
            help="Import all global stations instead of just African blocks (60–69).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Parse and validate without writing to the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after processing this many valid rows (useful for testing).",
        )

    def handle(self, *args, **options):
        africa_only = not options["no_africa_only"]
        dry_run = options["dry_run"]
        limit = options["limit"]
        source_url = options["source_url"]

        self.stdout.write(
            f"Importing WMO stations | africa_only={africa_only} "
            f"| dry_run={dry_run} | limit={limit} | url={source_url}"
        )

        importer = ISDStationImporter(csv_url=source_url)
        result = importer.run(africa_only=africa_only, dry_run=dry_run, limit=limit)

        tag = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{tag}Done — created={result.created} updated={result.updated} "
            f"skipped={result.skipped} errors={result.errors}"
        ))

        for msg in result.messages:
            self.stdout.write(self.style.WARNING(f"  ! {msg}"))
