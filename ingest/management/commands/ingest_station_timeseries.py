"""Load a folder of logger CSVs (campaign layout) into a station time-series dataset.

    manage.py ingest_station_timeseries <dataset_id> <folder>

Group / commune are taken from the folder layout, so a bulk load of a whole
campaign needs no extra metadata. Synchronous on purpose: it is the operator's
path for the initial bulk load, where progress output matters more than queueing.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from catalog.models import DatasetPage
from ingest.station_timeseries.service import StationTimeseriesIngestService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest station logger CSV files from a folder into a station_timeseries dataset."

    def add_arguments(self, parser) -> None:
        parser.add_argument("dataset_id")
        parser.add_argument("folder")
        parser.add_argument("--no-geocode", action="store_true",
                            help="Skip Nominatim place naming (offline / tests).")

    def handle(self, *args, **options) -> None:
        dataset = DatasetPage.objects.filter(dataset_id=options["dataset_id"]).first()
        if not dataset:
            raise CommandError(f"Unknown dataset_id '{options['dataset_id']}'")
        if dataset.dataset_type != "station_timeseries":
            raise CommandError("Dataset is not of type station_timeseries")

        folder = Path(options["folder"])
        files = sorted(p for p in folder.rglob("*") if p.suffix.lower() == ".csv")
        if not files:
            raise CommandError(f"No CSV files under {folder}")

        geocoder = _NoGeocoder() if options["no_geocode"] else None
        service = StationTimeseriesIngestService(geocoder=geocoder)
        for path in files:
            try:
                summary = service.ingest_file(
                    path, dataset_id=dataset.dataset_id, dataset_title=dataset.title
                )
            except Exception as exc:  # noqa: BLE001 - keep loading the rest
                logger.exception("Failed: %s", path)
                self.stderr.write(self.style.ERROR(f"{path.name}: {exc}"))
                continue
            self.stdout.write(
                f"{summary.station_code}: {summary.observations_written} obs, "
                f"{summary.rows_before_deployment} pre-deployment rows skipped"
            )


class _NoGeocoder:
    def place_name(self, lat: float, lon: float) -> str | None:
        return None
