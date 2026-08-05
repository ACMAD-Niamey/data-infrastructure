from __future__ import annotations

import datetime
import logging

from celery import shared_task
from django.utils import timezone

from .models import DownloadRun, DownloadWorkflow
from .services import workflow_runner

log = logging.getLogger(__name__)


def _is_due(run: DownloadRun, workflow: DownloadWorkflow, now: datetime.datetime) -> bool:
    if run.status == DownloadRun.Status.COMPLETED:
        return False
    if run.last_attempted_at and (now - run.last_attempted_at).total_seconds() < workflow.retry_interval_minutes * 60:
        return False
    return True


@shared_task
def run_due_download_workflows() -> None:
    """Beat entry (see CELERY_BEAT_SCHEDULE): fans out to process_download_run
    for each enabled workflow whose schedule/retry window is currently due.

    Self-healing: besides today, also re-checks the previous
    workflow.catch_up_days days and retries any that aren't COMPLETED yet -
    so an outage (Beat/worker down, a source that published late) is
    recovered automatically on the next tick, without operator intervention.
    Only today's run is gated by schedule_hour_utc/retry_until_hour_utc
    (there's no "time of day" for a day that's already past); catch-up days
    are only throttled by retry_interval_minutes.

    One static Beat entry polls frequently rather than one entry per workflow,
    so adding a new THREDDS source is an admin DB row, not a settings.py
    redeploy - matching the existing single "cleanup-wis2-downloads-daily"
    pattern.
    """
    now = timezone.now()
    today = now.date()

    for workflow in DownloadWorkflow.objects.filter(enabled=True):
        scheduled = now.replace(hour=workflow.schedule_hour_utc, minute=workflow.schedule_minute_utc, second=0, microsecond=0)
        cutoff = now.replace(hour=workflow.retry_until_hour_utc, minute=0, second=0, microsecond=0)
        today_is_due = scheduled <= now <= cutoff

        for offset in range(workflow.catch_up_days, -1, -1):
            run_date = today - datetime.timedelta(days=offset)
            if offset == 0 and not today_is_due:
                continue

            run, _ = DownloadRun.objects.get_or_create(workflow=workflow, run_date=run_date)
            if not _is_due(run, workflow, now):
                continue

            process_download_run.delay(run.id)


@shared_task
def process_download_run(run_id: int) -> dict:
    """Runs one DownloadRun to completion. Fanned out via .delay() from Beat
    (a run may cover many files and shouldn't block the Beat tick), while the
    per-item ingest call inside workflow_runner.execute() is synchronous -
    that call is already running inside its own worker context and needs the
    final IngestionRun status immediately, not a second round trip.
    """
    run = DownloadRun.objects.select_related("workflow").get(id=run_id)
    workflow_runner.execute(run)
    return {
        "run_id": run.id,
        "status": run.status,
        "total_files": run.total_files,
        "completed_files": run.completed_files,
        "failed_files": run.failed_files,
        "not_yet_available_files": run.not_yet_available_files,
    }
