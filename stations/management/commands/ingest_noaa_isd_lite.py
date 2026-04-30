"""Management command: ingest_noaa_isd_lite

Backfill NOAA ISD-Lite hourly observations for one or more (station, year)
combinations. Same code path runs inline or fans out to Celery via
``--dispatch-celery``.

Usage
-----
.. code-block:: bash

    # One station, one year
    python manage.py ingest_noaa_isd_lite --year 2023 --station-code 63740

    # All African synoptic stations, multi-year, via Celery
    python manage.py ingest_noaa_isd_lite --years 2020:2024 --africa-only --dispatch-celery

    # Dry run (fetch + parse only, no writes)
    python manage.py ingest_noaa_isd_lite --year 2023 --station-code 63740 --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from stations.models import Station
from stations.services.isd_lite_importer import ISDLiteImporter


_AFRICA_WMO_BLOCK_MIN = 60000
_AFRICA_WMO_BLOCK_MAX = 69999


class Command(BaseCommand):
    help = "Backfill NOAA ISD-Lite hourly observations into the observations table."

    def add_arguments(self, parser):
        years = parser.add_mutually_exclusive_group(required=True)
        years.add_argument(
            "--year",
            type=int,
            help="Single year (e.g. 2023).",
        )
        years.add_argument(
            "--years",
            type=str,
            help="Inclusive year range, e.g. 2020:2024.",
        )

        selectors = parser.add_mutually_exclusive_group()
        selectors.add_argument(
            "--station-code",
            action="append",
            default=None,
            help="Restrict to a specific station_code (repeatable).",
        )
        selectors.add_argument(
            "--africa-only",
            action="store_true",
            default=False,
            help="Restrict to African WMO blocks (60000-69999). Default if no other selector is given.",
        )

        parser.add_argument(
            "--dispatch-celery",
            action="store_true",
            default=False,
            help="Enqueue tasks instead of running inline.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Fetch + parse without writing to the database.",
        )

    def handle(self, *args, **options):
        years = self._resolve_years(options)
        station_codes: list[str] | None = options["station_code"]
        africa_only: bool = options["africa_only"]
        dispatch_celery: bool = options["dispatch_celery"]
        dry_run: bool = options["dry_run"]

        # Default selector when none given.
        if not station_codes and not africa_only:
            africa_only = True

        stations = self._select_stations(station_codes=station_codes, africa_only=africa_only)
        if not stations:
            self.stdout.write(self.style.WARNING("No matching stations; nothing to do."))
            return

        if dispatch_celery and dry_run:
            raise CommandError("--dispatch-celery and --dry-run are mutually exclusive.")

        self.stdout.write(
            f"Ingesting ISD-Lite | years={years} stations={len(stations)} "
            f"dispatch_celery={dispatch_celery} dry_run={dry_run}"
        )

        if dispatch_celery:
            self._dispatch(stations, years)
            return

        self._run_inline(stations, years, dry_run=dry_run)

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _resolve_years(options: dict) -> list[int]:
        if options["year"] is not None:
            return [int(options["year"])]
        raw = (options["years"] or "").strip()
        if ":" not in raw:
            raise CommandError("--years must be in the form START:END (e.g. 2020:2024).")
        try:
            start_s, end_s = raw.split(":", 1)
            start = int(start_s)
            end = int(end_s)
        except ValueError as exc:
            raise CommandError(f"Invalid --years value: {raw!r}") from exc
        if end < start:
            raise CommandError("--years end must be >= start.")
        return list(range(start, end + 1))

    @staticmethod
    def _select_stations(*, station_codes: list[str] | None, africa_only: bool) -> list[Station]:
        qs = Station.objects.all().order_by("station_code")
        if station_codes:
            qs = qs.filter(station_code__in=station_codes)
        elif africa_only:
            # WMO blocks 60-69 -> station_code (== wmo_id) starts with 6.
            qs = qs.filter(station_code__regex=r"^6\d{4}$")
        return list(qs)

    def _dispatch(self, stations: list[Station], years: list[int]) -> None:
        from stations.tasks import ingest_isd_lite_year  # local import: keeps celery optional

        enqueued = 0
        for station in stations:
            for year in years:
                ingest_isd_lite_year.delay(station.id, year)
                enqueued += 1
        self.stdout.write(self.style.SUCCESS(f"Enqueued {enqueued} (station, year) tasks."))

    def _run_inline(self, stations: list[Station], years: list[int], *, dry_run: bool) -> None:
        importer = ISDLiteImporter()
        totals = {"parsed": 0, "written": 0, "skipped_existing": 0, "errors": 0, "missing": 0}
        for station in stations:
            for year in years:
                result = importer.import_year(station=station, year=year, dry_run=dry_run)
                totals["parsed"] += result.parsed
                totals["written"] += result.written
                totals["skipped_existing"] += result.skipped_existing
                if result.error:
                    totals["errors"] += 1
                    if result.error == "archive not found":
                        totals["missing"] += 1
                self.stdout.write(
                    f"station={result.station_code} year={result.year} "
                    f"parsed={result.parsed} written={result.written} "
                    f"skipped_existing={result.skipped_existing} "
                    f"error={result.error or '-'}"
                )
        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Done. "
            f"parsed={totals['parsed']} written={totals['written']} "
            f"skipped_existing={totals['skipped_existing']} "
            f"errors={totals['errors']} missing_archives={totals['missing']}"
        ))
