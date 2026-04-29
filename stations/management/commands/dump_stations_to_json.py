"""Management command: dump_stations_to_json

Serialize Station rows to NDJSON for migration to another environment
(typically: locally-enriched stations -> production).

Scope: ONLY the ``stations`` table is exported.
- ``id`` is intentionally omitted so the destination can assign its own PKs.
- ``geom`` is exported as WKT and rehydrated by ``load_stations_from_json``.
- ``station_aliases``, ``station_sensors``, and ``observations`` are NOT exported;
  aliases/sensors are recreated by MQTT ingestion on first message and the
  observed-station migration deliberately doesn't move observations.

Pair with: ``load_stations_from_json``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from stations.models import Station


_FIELDS = (
    "station_code",
    "wmo_id",
    "name",
    "country_code",
    "canonical_code",
    "country_name",
    "admin1",
    "admin2",
    "elevation_m",
    "agency",
    "station_type",
    "install_date",
    "is_active",
    "description",
)


class Command(BaseCommand):
    help = (
        "Dump Station rows to NDJSON for migration. Geometry is exported as WKT. "
        "Aliases, sensors, and observations are not included."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "output_path",
            type=str,
            help="Destination NDJSON file (one station per line).",
        )
        parser.add_argument(
            "--station-type",
            action="append",
            default=None,
            help=(
                "Restrict by Station.station_type (repeatable). "
                "Choices match Station.StationType (synop, aws, agro, ...). "
                "Default: all types."
            ),
        )
        parser.add_argument(
            "--only-missing-canonical",
            action="store_true",
            default=False,
            help="Only dump stations whose canonical_code is NULL/empty.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after N rows (smoke testing).",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output_path"]).expanduser()
        station_types: list[str] | None = options["station_type"]
        only_missing_canonical: bool = options["only_missing_canonical"]
        limit: int | None = options["limit"]

        qs = Station.objects.all().order_by("station_code")
        if station_types:
            qs = qs.filter(station_type__in=station_types)
        if only_missing_canonical:
            qs = qs.filter(canonical_code__isnull=True) | qs.filter(canonical_code__exact="")
            qs = qs.distinct().order_by("station_code")
        if limit is not None:
            qs = qs[:limit]

        if not output_path.parent.exists():
            raise CommandError(f"Output directory does not exist: {output_path.parent}")

        dumped = 0
        skipped_no_geom = 0
        with output_path.open("w", encoding="utf-8") as fh:
            for station in qs.iterator(chunk_size=500):
                if station.geom is None:
                    skipped_no_geom += 1
                    continue
                fh.write(json.dumps(self._serialize(station), ensure_ascii=False))
                fh.write("\n")
                dumped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"dumped={dumped} skipped_no_geom={skipped_no_geom} path={output_path}"
            )
        )

    @staticmethod
    def _serialize(station: Station) -> dict:
        payload: dict = {field: getattr(station, field) for field in _FIELDS}
        for key, value in list(payload.items()):
            if isinstance(value, Decimal):
                payload[key] = float(value)
            elif isinstance(value, (date, datetime)):
                payload[key] = value.isoformat()
        payload["geom_wkt"] = station.geom.wkt if station.geom else None
        return payload
