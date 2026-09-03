"""Management command: seed_precipitation_tercile_workflow

One-shot, idempotent seeding of the ACMAD *precipitation tercile, monthly*
product - three THREDDS sources (RFE2, CPC-UNI, CAMSO-PI) ingested into three
STAC collections under a single ``DatasetPage``.

Unlike the ``catalog`` seed migrations, this depends on Wagtail page content
(the ``DatasetPage`` lives under a project the operator chooses), so it's a
re-runnable command rather than a migration. It does NOT create the
``DatasetPage`` - create that in Wagtail first (``dataset_id`` =
``precipitation-tercile-monthly``, cadence Monthly, "allow multiple layer
styles" checked), then run this.

What it creates / updates (all ``update_or_create`` - safe to re-run):

* three ``Layer`` styles under the dataset, one per source, each carrying its
  own ``stac_collection_id`` (== its ``layer_id``);
* one monthly ``DownloadWorkflow`` pointed at ``OBS_RAIN_ANOM/monthly``;
* three ``DownloadWorkflowFile`` rows, one per source/layer.

After running, backfill with (see printed output):

    python manage.py run_download_workflow \\
      --workflow-name "ACMAD OBS_RAIN_ANOM tercile monthly" \\
      --run-month-range 2000-01:<this-month> --dispatch-celery
"""

from __future__ import annotations

import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

DATASET_ID = "precipitation-tercile-monthly"
WORKFLOW_NAME = "ACMAD OBS_RAIN_ANOM tercile monthly"
SOURCE_BASE_URL = (
    "https://sgbd.acmad.org/thredds/fileServer/ACMAD/CDD/ClimateBulletin_TN/OBS_RAIN_ANOM/monthly"
)

# (source token as it appears in the THREDDS filename, layer/collection slug, human label, earliest year)
SOURCES = [
    ("CPC-UNI", "precipitation-tercile-cpc-uni", "CPC-UNI (gauge, 2000-)", 2000),
    ("RFE2", "precipitation-tercile-rfe2", "RFE2 (satellite-gauge, 2023-)", 2023),
    ("CAMSO-PI", "precipitation-tercile-camso-pi", "CAMSO-PI (2000-)", 2000),
]
PRIMARY_SLUG = "precipitation-tercile-cpc-uni"  # longest record -> default_visible


class Command(BaseCommand):
    help = "Seed the precipitation-tercile-monthly Layer styles + THREDDS download workflow (3 sources)."

    @transaction.atomic
    def handle(self, *args, **options):
        from catalog.models import DatasetPage, Layer
        from thredds_ingestion.models import DownloadWorkflow, DownloadWorkflowFile

        dataset = DatasetPage.objects.filter(dataset_id=DATASET_ID).first()
        if not dataset:
            raise CommandError(
                f"DatasetPage '{DATASET_ID}' does not exist. Create it in Wagtail first "
                f"(under the relevant project, cadence=Monthly, 'allow multiple layer styles' checked), "
                f"then re-run this command."
            )
        if dataset.cadence != "monthly":
            raise CommandError(
                f"DatasetPage '{DATASET_ID}' has cadence '{dataset.cadence}', expected 'monthly'."
            )
        if not dataset.allow_multiple_layers:
            dataset.allow_multiple_layers = True
            dataset.save()
            self.stdout.write(self.style.WARNING("  set allow_multiple_layers=True on the dataset"))

        # 1. Layer styles - one per source.
        layers: dict[str, Layer] = {}
        for _src, slug, label, _year in SOURCES:
            layer, created = Layer.objects.update_or_create(
                layer_id=slug,
                defaults={
                    "dataset": dataset,
                    "title": f"Precipitation tercile - {label}",
                    "layer_type": "raster",
                    "has_stac_collection": True,
                    "stac_collection_id": slug,
                    "default_visible": (slug == PRIMARY_SLUG),
                },
            )
            layers[slug] = layer
            self.stdout.write(f"  {'created' if created else 'updated'} layer {slug}")

        # 2. Workflow - monthly cadence, {month_abbr}/tif dated folder.
        workflow, created = DownloadWorkflow.objects.update_or_create(
            name=WORKFLOW_NAME,
            defaults={
                "source_base_url": SOURCE_BASE_URL,
                "folder_pattern": "{month_abbr}/tif",
                "cadence": DownloadWorkflow.Cadence.MONTHLY,
                "schedule_day_of_month": 15,
                "enabled": True,
            },
        )
        self.stdout.write(f"  {'created' if created else 'updated'} workflow {WORKFLOW_NAME!r}")

        # 3. One file mapping per source, keyed on (workflow, layer).
        for i, (src, slug, label, _year) in enumerate(SOURCES):
            _, created = DownloadWorkflowFile.objects.update_or_create(
                workflow=workflow,
                layer=layers[slug],
                defaults={
                    "dataset": dataset,
                    "label": label,
                    "filename_pattern": f"AFR_{{month_abbr}}_{{run_date:%Y}}_{src}_Tercile.tif",
                    "lead_hours_csv": "",
                    "sort_order": i,
                    "enabled": True,
                },
            )
            self.stdout.write(f"  {'created' if created else 'updated'} file mapping {src} -> {slug}")

        this_month = dt.date.today().strftime("%Y-%m")
        self.stdout.write(self.style.SUCCESS("\nSeed complete. Backfill from the earliest available month:\n"))
        self.stdout.write(
            f"  python manage.py run_download_workflow --workflow-name {WORKFLOW_NAME!r} "
            f"--run-month-range 2000-01:{this_month} --dry-run\n"
            f"  python manage.py run_download_workflow --workflow-name {WORKFLOW_NAME!r} "
            f"--run-month-range 2000-01:{this_month} --dispatch-celery\n"
        )
        self.stdout.write(
            "RFE2 only goes back to 2023 - earlier months resolve to not_yet_available and are skipped.\n"
            "Celery Beat then keeps each new month current automatically."
        )
