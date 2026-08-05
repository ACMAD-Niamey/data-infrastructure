"""Management command: run_download_workflow

Run one or more THREDDS DownloadWorkflows for one or more run_dates: resolve
each mapped file's URL, check/download it, and push it through the existing
upload/ingest pipeline. Same code path runs inline or fans out to Celery via
``--dispatch-celery``. Reruns are safe - already-completed items are skipped
(see thredds_ingestion.services.workflow_runner), so a backfill range can be
re-run freely without duplicating work.

Usage
-----
.. code-block:: bash

    # One workflow, one date
    python manage.py run_download_workflow --workflow-name "ACMAD WWFD ensemble5" --run-date 2026-08-05

    # Backfill a date range, via Celery (recommended for large ranges - lets
    # workers process dates in parallel instead of one at a time inline)
    python manage.py run_download_workflow --workflow-id 3 --run-date-range 2026-07-01:2026-08-05 --dispatch-celery

    # Backfill the last 14 days (inclusive of today)
    python manage.py run_download_workflow --all-enabled --days-back 14

    # Dry run (pattern rendering + THREDDS existence checks only, no download/ingest)
    python manage.py run_download_workflow --workflow-id 3 --run-date 2026-08-01 --dry-run

    # Force re-ingest even if items already completed
    python manage.py run_download_workflow --workflow-id 3 --run-date 2026-08-05 --force
"""

from __future__ import annotations

import datetime as dt

from django.core.management.base import BaseCommand, CommandError

from thredds_ingestion.models import DownloadRun, DownloadWorkflow
from thredds_ingestion.services import workflow_runner


class Command(BaseCommand):
    help = "Run one or more THREDDS download workflows for one or more run_dates."

    def add_arguments(self, parser):
        selectors = parser.add_mutually_exclusive_group()
        selectors.add_argument(
            "--workflow-id",
            action="append",
            type=int,
            default=None,
            help="Restrict to a specific DownloadWorkflow id (repeatable).",
        )
        selectors.add_argument(
            "--workflow-name",
            action="append",
            default=None,
            help="Restrict to a specific DownloadWorkflow name (repeatable).",
        )
        selectors.add_argument(
            "--all-enabled",
            action="store_true",
            default=False,
            help="Run every enabled workflow. Default if no other selector is given.",
        )

        dates = parser.add_mutually_exclusive_group(required=True)
        dates.add_argument(
            "--run-date",
            type=str,
            help="Single forecast issue date, YYYY-MM-DD.",
        )
        dates.add_argument(
            "--run-date-range",
            type=str,
            help="Inclusive date range for a backfill, START:END, e.g. 2026-07-01:2026-08-05.",
        )
        dates.add_argument(
            "--days-back",
            type=int,
            help="Backfill convenience: the last N days through today (inclusive), e.g. 14.",
        )

        parser.add_argument(
            "--dispatch-celery",
            action="store_true",
            default=False,
            help=(
                "Enqueue one process_download_run task per (workflow, run_date) instead of "
                "running inline. Recommended for backfills spanning many dates."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Resolve patterns and check THREDDS existence only - no download, upload, or ingest.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Re-download/re-ingest even if a DownloadRunItem already completed, for this invocation only.",
        )

    def handle(self, *args, **options):
        workflow_ids: list[int] | None = options["workflow_id"]
        workflow_names: list[str] | None = options["workflow_name"]
        all_enabled: bool = options["all_enabled"]
        dispatch_celery: bool = options["dispatch_celery"]
        dry_run: bool = options["dry_run"]
        force: bool = options["force"]

        if not workflow_ids and not workflow_names and not all_enabled:
            all_enabled = True

        if dispatch_celery and dry_run:
            raise CommandError("--dispatch-celery and --dry-run are mutually exclusive.")

        run_dates = self._resolve_run_dates(options)
        workflows = self._select_workflows(
            workflow_ids=workflow_ids, workflow_names=workflow_names, all_enabled=all_enabled
        )
        if not workflows:
            self.stdout.write(self.style.WARNING("No matching workflows; nothing to do."))
            return

        self.stdout.write(
            f"Running THREDDS ingestion | dates={run_dates[0]}..{run_dates[-1]} ({len(run_dates)}) "
            f"workflows={len(workflows)} dispatch_celery={dispatch_celery} dry_run={dry_run} force={force}"
        )

        if dispatch_celery:
            self._dispatch(workflows, run_dates)
            return

        self._run_inline(workflows, run_dates, dry_run=dry_run, force=force)

    # ---- helpers -----------------------------------------------------------

    @classmethod
    def _resolve_run_dates(cls, options: dict) -> list[dt.date]:
        if options["run_date"]:
            return [cls._parse_date(options["run_date"], "--run-date")]

        if options["run_date_range"]:
            raw = options["run_date_range"]
            if ":" not in raw:
                raise CommandError("--run-date-range must be START:END (e.g. 2026-07-01:2026-08-05).")
            start_s, end_s = raw.split(":", 1)
            start = cls._parse_date(start_s, "--run-date-range start")
            end = cls._parse_date(end_s, "--run-date-range end")
            if end < start:
                raise CommandError("--run-date-range end must be >= start.")
            days = (end - start).days
            return [start + dt.timedelta(days=i) for i in range(days + 1)]

        days_back = options["days_back"]
        if days_back <= 0:
            raise CommandError("--days-back must be > 0.")
        today = dt.date.today()
        start = today - dt.timedelta(days=days_back - 1)
        return [start + dt.timedelta(days=i) for i in range(days_back)]

    @staticmethod
    def _parse_date(raw: str, label: str) -> dt.date:
        try:
            return dt.datetime.strptime(raw.strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError(f"{label} must be YYYY-MM-DD, got {raw!r}") from exc

    @staticmethod
    def _select_workflows(
        *, workflow_ids: list[int] | None, workflow_names: list[str] | None, all_enabled: bool
    ) -> list[DownloadWorkflow]:
        qs = DownloadWorkflow.objects.all().order_by("name")
        if workflow_ids:
            qs = qs.filter(id__in=workflow_ids)
        elif workflow_names:
            qs = qs.filter(name__in=workflow_names)
        elif all_enabled:
            qs = qs.filter(enabled=True)
        return list(qs)

    def _dispatch(self, workflows: list[DownloadWorkflow], run_dates: list[dt.date]) -> None:
        from thredds_ingestion.tasks import process_download_run

        enqueued = 0
        for workflow in workflows:
            for run_date in run_dates:
                run, _ = DownloadRun.objects.get_or_create(workflow=workflow, run_date=run_date)
                process_download_run.delay(run.id)
                enqueued += 1
        self.stdout.write(self.style.SUCCESS(f"Enqueued {enqueued} workflow run(s)."))

    def _run_inline(
        self, workflows: list[DownloadWorkflow], run_dates: list[dt.date], *, dry_run: bool, force: bool
    ) -> None:
        totals = {"total": 0, "completed": 0, "failed": 0, "not_yet_available": 0}
        for workflow in workflows:
            for run_date in run_dates:
                run, _ = DownloadRun.objects.get_or_create(workflow=workflow, run_date=run_date)
                run = workflow_runner.execute(run, force=force, dry_run=dry_run)

                totals["total"] += run.total_files
                totals["completed"] += run.completed_files
                totals["failed"] += run.failed_files
                totals["not_yet_available"] += run.not_yet_available_files

                self.stdout.write(
                    f"workflow={workflow.name} run_date={run_date} status={run.status} "
                    f"total={run.total_files} completed={run.completed_files} "
                    f"failed={run.failed_files} not_yet_available={run.not_yet_available_files}"
                )

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Done. "
            f"total={totals['total']} completed={totals['completed']} "
            f"failed={totals['failed']} not_yet_available={totals['not_yet_available']}"
        ))
