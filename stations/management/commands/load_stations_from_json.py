"""Management command: load_stations_from_json

Idempotent counterpart to ``dump_stations_to_json``. Reads NDJSON and inserts
rows into the local ``stations`` table. Conflicts on ``station_code`` (which is
``unique=True``) are silently skipped via ``bulk_create(ignore_conflicts=True)``,
so re-running the command is a safe no-op.

No external API calls are made (no Nominatim, no boundary recompute). Imported
``country_name``, ``admin1``, ``admin2``, and ``canonical_code`` values are
written verbatim, preserving any enrichment performed in the source environment.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError

from stations.models import Station


_REQUIRED = ("station_code", "name", "geom_wkt")
_DATE_FIELDS = ("install_date",)


class Command(BaseCommand):
    help = (
        "Load Station rows from an NDJSON file produced by dump_stations_to_json. "
        "Idempotent on station_code (unique). No external API calls."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "input_path",
            type=str,
            help="NDJSON file produced by dump_stations_to_json.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Chunk size for bulk_create (default: 500).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Parse and validate input; do not write to the database.",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input_path"]).expanduser()
        batch_size: int = options["batch_size"]
        dry_run: bool = options["dry_run"]

        if not input_path.is_file():
            raise CommandError(f"Input file not found: {input_path}")

        records: list[Station] = []
        total = 0
        invalid = 0
        invalid_messages: list[str] = []

        with input_path.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                total += 1
                try:
                    payload = json.loads(raw)
                    station = self._build_station(payload)
                except (ValueError, KeyError, TypeError) as exc:
                    invalid += 1
                    if len(invalid_messages) < 5:
                        invalid_messages.append(f"line {line_no}: {exc}")
                    continue
                records.append(station)

        if invalid:
            for msg in invalid_messages:
                self.stdout.write(self.style.WARNING(f"  ! {msg}"))
            self.stdout.write(self.style.WARNING(f"  invalid_rows={invalid} (skipped)"))

        existing = set(
            Station.objects
            .filter(station_code__in=[s.station_code for s in records])
            .values_list("station_code", flat=True)
        )
        to_create = [s for s in records if s.station_code not in existing]
        existing_count = len(records) - len(to_create)

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY-RUN] total={total} invalid={invalid} "
                    f"existing={existing_count} would_create={len(to_create)}"
                )
            )
            return

        created = 0
        if to_create:
            saved = Station.objects.bulk_create(
                to_create,
                batch_size=batch_size,
                ignore_conflicts=True,
            )
            created = sum(1 for s in saved if s.pk is not None)

        self.stdout.write(
            self.style.SUCCESS(
                f"total={total} invalid={invalid} existing={existing_count} "
                f"created={created} skipped={len(to_create) - created}"
            )
        )

    @staticmethod
    def _build_station(payload: dict) -> Station:
        for field in _REQUIRED:
            if not payload.get(field):
                raise ValueError(f"missing required field: {field}")

        geom = GEOSGeometry(payload["geom_wkt"], srid=4326)

        kwargs: dict = {}
        for key in (
            "station_code",
            "wmo_id",
            "name",
            "country_code",
            "canonical_code",
            "country_name",
            "admin1",
            "admin2",
            "agency",
            "station_type",
            "is_active",
            "description",
            "elevation_m",
        ):
            if key in payload:
                kwargs[key] = payload[key]

        for field in _DATE_FIELDS:
            value = payload.get(field)
            if isinstance(value, str) and value:
                try:
                    kwargs[field] = datetime.fromisoformat(value).date()
                except ValueError:
                    kwargs[field] = date.fromisoformat(value)
            elif value is None:
                kwargs[field] = None

        kwargs.setdefault("station_type", Station.StationType.AWS)
        kwargs.setdefault("is_active", True)

        return Station(geom=geom, **kwargs)
