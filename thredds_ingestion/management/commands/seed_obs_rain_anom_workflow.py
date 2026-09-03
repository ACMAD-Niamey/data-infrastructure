"""Management command: seed_obs_rain_anom_workflow

Wire up a THREDDS ``DownloadWorkflow`` for one ACMAD *OBS_RAIN_ANOM* product
(Tercile / Percentile / Quintile / Pnorm / Precip-Anom / ...), mapping its
per-source GeoTIFFs onto ``Layer`` styles that **already exist** under a
``DatasetPage``.

This command does NOT create the ``DatasetPage`` or the ``Layer`` styles - you
create those in Wagtail admin (dataset page with "allow multiple layer styles"
checked, then one Layer style per source, picking the dataset from the dropdown
and setting its ``stac_collection_id`` under *Layer details*). This command only
looks them up, validates them, and creates the download workflow + one file
mapping per source. Idempotent (``update_or_create``) - safe to re-run.

Monthly example (dataset + 3 layer styles already in Wagtail):

    python manage.py seed_obs_rain_anom_workflow \\
      --dataset-id pecipitation-tercile-monthly --variable Tercile \\
      --layer CPC-UNI=pecipitation-tercile-cpc-uni-monthly \\
      --layer RFE2=pecipitation-tercile-rfe2-monthly \\
      --layer CAMSO-PI=pecipitation-tercile-camso-pi-monthly \\
      --primary CPC-UNI

Seasonal example (one workflow per season - the season is a literal folder):

    python manage.py seed_obs_rain_anom_workflow \\
      --dataset-id pecipitation-tercile-jja --variable Tercile \\
      --period seasonal --season JJA --anchor-month 6 \\
      --layer CPC-UNI=pecipitation-tercile-jja-cpc-uni
"""

from __future__ import annotations

import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

FILESERVER_ROOT = "https://sgbd.acmad.org/thredds/fileServer/ACMAD/CDD/ClimateBulletin_TN/OBS_RAIN_ANOM"

# THREDDS source tokens as they appear in AFR_<Mon>_<YYYY>_<SOURCE>_<VAR>.tif
KNOWN_SOURCES = {"RFE2", "CPC-UNI", "CAMSO-PI", "CHIRPS"}
# Filename variable tokens seen in the OBS_RAIN_ANOM folders.
KNOWN_VARIABLES = {
    "Tot", "Tercile", "Ranking_Percentile", "Quintile",
    "Precip-Anom", "Pnorm", "Percentile", "Climo",
}


class Command(BaseCommand):
    help = "Wire a THREDDS download workflow for one OBS_RAIN_ANOM product onto existing Layer styles."

    def add_arguments(self, parser):
        parser.add_argument("--dataset-id", required=True)
        parser.add_argument("--variable", required=True, help=f"One of {sorted(KNOWN_VARIABLES)}")
        parser.add_argument(
            "--layer", action="append", default=[], metavar="SOURCE=layer_id",
            help="Repeatable. Maps a THREDDS source token to an existing Layer style's layer_id.",
        )
        parser.add_argument("--primary", default="", help="SOURCE whose layer is default_visible (optional).")
        parser.add_argument("--period", choices=["monthly", "seasonal"], default="monthly")
        parser.add_argument("--season", default="", help="Season folder, e.g. JJA (required for --period seasonal).")
        parser.add_argument("--anchor-month", type=int, default=0, help="1-12, first month of the season (seasonal only).")
        parser.add_argument("--workflow-name", default="", help="Override the generated workflow name.")
        parser.add_argument("--schedule-day-of-month", type=int, default=15)
        parser.add_argument("--dry-run", action="store_true", help="Print what would change, touch nothing.")

    def handle(self, *args, **opts):
        from catalog.models import DatasetPage
        from thredds_ingestion.models import DownloadWorkflow, DownloadWorkflowFile

        variable = opts["variable"]
        if variable not in KNOWN_VARIABLES:
            raise CommandError(f"--variable {variable!r} not in {sorted(KNOWN_VARIABLES)}")

        mappings = self._parse_layers(opts["layer"])
        if opts["primary"] and opts["primary"] not in mappings:
            raise CommandError(f"--primary {opts['primary']!r} is not among --layer sources {list(mappings)}")

        seasonal = opts["period"] == "seasonal"
        if seasonal and not (opts["season"] and 1 <= opts["anchor_month"] <= 12):
            raise CommandError("--period seasonal requires --season and --anchor-month (1-12).")

        dataset = DatasetPage.objects.filter(dataset_id=opts["dataset_id"]).first()
        if not dataset:
            raise CommandError(f"DatasetPage {opts['dataset_id']!r} not found - create it in Wagtail first.")
        expected_cadence = "seasonal" if seasonal else "monthly"
        if dataset.cadence != expected_cadence:
            raise CommandError(f"DatasetPage cadence is {dataset.cadence!r}, expected {expected_cadence!r}.")
        if len(mappings) > 1 and not dataset.allow_multiple_layers:
            raise CommandError(
                "This maps multiple layers but the dataset does not allow multiple layer styles - "
                "check 'allow multiple layer styles' on the dataset page."
            )

        layers = self._resolve_layers(dataset, mappings)

        folder = f"{opts['season']}/tif" if seasonal else "{month_abbr}/tif"
        base_url = f"{FILESERVER_ROOT}/{'seasonal' if seasonal else 'monthly'}"
        name = opts["workflow_name"] or (
            f"ACMAD OBS_RAIN_ANOM {variable.lower()} "
            f"{opts['season'].lower() if seasonal else 'monthly'}"
        )

        wf_defaults = dict(
            source_base_url=base_url,
            folder_pattern=folder,
            cadence=DownloadWorkflow.Cadence.SEASONAL if seasonal else DownloadWorkflow.Cadence.MONTHLY,
            schedule_day_of_month=opts["schedule_day_of_month"],
            enabled=True,
        )
        if seasonal:
            wf_defaults["anchor_month"] = opts["anchor_month"]

        self.stdout.write(f"workflow: {name!r}  base={base_url}  folder={folder!r}")
        for source, layer in layers.items():
            fname = (
                f"AFR_{opts['season']}_{{run_date:%Y}}_{source}_{variable}.tif" if seasonal
                else f"AFR_{{month_abbr}}_{{run_date:%Y}}_{source}_{variable}.tif"
            )
            self.stdout.write(f"  {source:9s} -> layer {layer.layer_id}  (collection {layer.effective_stac_collection})  {fname}")

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("\n[dry-run] nothing written."))
            return

        with transaction.atomic():
            workflow, created = DownloadWorkflow.objects.update_or_create(name=name, defaults=wf_defaults)
            self.stdout.write(f"{'created' if created else 'updated'} workflow {name!r}")

            for i, (source, layer) in enumerate(layers.items()):
                fname = (
                    f"AFR_{opts['season']}_{{run_date:%Y}}_{source}_{variable}.tif" if seasonal
                    else f"AFR_{{month_abbr}}_{{run_date:%Y}}_{source}_{variable}.tif"
                )
                _, created = DownloadWorkflowFile.objects.update_or_create(
                    workflow=workflow, layer=layer,
                    defaults=dict(
                        dataset=dataset, label=source, filename_pattern=fname,
                        lead_hours_csv="", sort_order=i, enabled=True,
                    ),
                )
                self.stdout.write(f"  {'created' if created else 'updated'} file mapping {source}")

        end = dt.date.today().strftime("%Y-%m")
        start = "1998-01" if seasonal else "2000-01"
        self.stdout.write(self.style.SUCCESS(f"\nDone. Backfill:\n"))
        self.stdout.write(
            f"  python manage.py run_download_workflow --workflow-name {name!r} "
            f"--run-month-range {start}:{end} --dry-run\n"
            f"  python manage.py run_download_workflow --workflow-name {name!r} "
            f"--run-month-range {start}:{end} --dispatch-celery"
        )
        self.stdout.write("(RFE2 records start ~2023; earlier months resolve to not_yet_available and are skipped.)")

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _parse_layers(raw: list[str]) -> dict[str, str]:
        if not raw:
            raise CommandError("at least one --layer SOURCE=layer_id is required")
        out: dict[str, str] = {}
        for item in raw:
            if "=" not in item:
                raise CommandError(f"--layer must be SOURCE=layer_id, got {item!r}")
            source, layer_id = (p.strip() for p in item.split("=", 1))
            if source not in KNOWN_SOURCES:
                raise CommandError(f"--layer source {source!r} not in {sorted(KNOWN_SOURCES)}")
            if not layer_id:
                raise CommandError(f"--layer {item!r} has an empty layer_id")
            out[source] = layer_id
        return out

    def _resolve_layers(self, dataset, mappings: dict[str, str]):
        from catalog.models import Layer

        resolved = {}
        for source, layer_id in mappings.items():
            try:
                layer = Layer.objects.get(layer_id=layer_id)
            except Layer.DoesNotExist:
                raise CommandError(f"Layer style {layer_id!r} not found - create it in Wagtail under {dataset.dataset_id!r}.")
            if layer.dataset_id != dataset.pk:
                raise CommandError(
                    f"Layer {layer_id!r} belongs to a different dataset ({layer.dataset.dataset_id!r}), not {dataset.dataset_id!r}."
                )
            if not layer.has_stac_collection:
                self.stdout.write(self.style.WARNING(f"  {layer_id}: has_stac_collection is unchecked"))
            if not layer.stac_collection_id:
                self.stdout.write(
                    self.style.WARNING(f"  {layer_id}: stac_collection_id blank - ingestion will use layer_id {layer_id!r}")
                )
            resolved[source] = layer
        return resolved
