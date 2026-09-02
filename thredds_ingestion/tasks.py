from __future__ import annotations

import datetime
import logging

from celery import shared_task
from django.utils import timezone

from .models import DownloadRun, DownloadWorkflow
from .services import workflow_runner
from .services.dates import add_months

log = logging.getLogger(__name__)


def _is_due(run: DownloadRun, workflow: DownloadWorkflow, now: datetime.datetime) -> bool:
    if run.status in (DownloadRun.Status.COMPLETED, DownloadRun.Status.RUNNING):
        return False
    if run.last_attempted_at and (now - run.last_attempted_at).total_seconds() < workflow.retry_interval_minutes * 60:
        return False
    return True


def _candidate_run_dates(workflow: DownloadWorkflow, now: datetime.datetime) -> list[datetime.date]:
    """run_dates this workflow should attempt on this tick, before the per-run
    _is_due throttle. Newest period first is irrelevant here (each is
    dispatched independently), but the newest period is the one gated by a
    publish window - older ones only self-heal until they scroll out of
    catch_up."""
    today = now.date()
    if workflow.cadence == DownloadWorkflow.Cadence.MONTHLY:
        return _monthly_candidate_run_dates(workflow, today)
    if workflow.cadence == DownloadWorkflow.Cadence.SEASONAL:
        return _seasonal_candidate_run_dates(workflow, today)
    return _daily_candidate_run_dates(workflow, now, today)


def _daily_candidate_run_dates(
    workflow: DownloadWorkflow, now: datetime.datetime, today: datetime.date
) -> list[datetime.date]:
    scheduled = now.replace(
        hour=workflow.schedule_hour_utc, minute=workflow.schedule_minute_utc, second=0, microsecond=0
    )
    cutoff = now.replace(hour=workflow.retry_until_hour_utc, minute=0, second=0, microsecond=0)
    today_is_due = scheduled <= now <= cutoff

    dates: list[datetime.date] = []
    for offset in range(workflow.catch_up_days, -1, -1):
        if offset == 0 and not today_is_due:
            continue
        dates.append(today - datetime.timedelta(days=offset))
    return dates


def _within_publish_window(
    workflow: DownloadWorkflow, today: datetime.date, publish_day: datetime.date
) -> bool:
    """The newest monthly/seasonal period is only attempted from its publish
    day (schedule_day_of_month of the publish month) until retry_window_days
    later - the upstream observed batch lands in that window, and there's no
    point hammering a HEAD 404 the rest of the time."""
    return publish_day <= today <= publish_day + datetime.timedelta(days=workflow.retry_window_days)


def _monthly_candidate_run_dates(
    workflow: DownloadWorkflow, today: datetime.date
) -> list[datetime.date]:
    # The current calendar month's data doesn't exist yet (month's not over),
    # so the newest target is last month; its publish day is
    # schedule_day_of_month of *this* month.
    newest = add_months(today.replace(day=1), -1)
    publish_day = today.replace(day=min(workflow.schedule_day_of_month, 28))

    dates: list[datetime.date] = []
    for i in range(workflow.catch_up_periods):
        if i == 0 and not _within_publish_window(workflow, today, publish_day):
            continue
        dates.append(add_months(newest, -i))
    return dates


def _seasonal_candidate_run_dates(
    workflow: DownloadWorkflow, today: datetime.date
) -> list[datetime.date]:
    dates: list[datetime.date] = []
    for i in range(workflow.catch_up_periods):
        anchor = datetime.date(today.year - i, workflow.anchor_month, 1)
        publish_day = add_months(anchor, workflow.publish_month_offset).replace(
            day=min(workflow.schedule_day_of_month, 28)
        )
        if i == 0:
            if not _within_publish_window(workflow, today, publish_day):
                continue
        elif today < publish_day:
            # A past year whose publish day is still in the future (we're early
            # in the current year) - that season hasn't happened yet.
            continue
        dates.append(anchor)
    return dates


@shared_task
def run_due_download_workflows() -> None:
    """Beat entry (see CELERY_BEAT_SCHEDULE): fans out to process_download_run
    for each enabled workflow whose schedule/retry window is currently due.

    Self-healing: besides the current period, also re-checks the previous
    workflow.catch_up_days periods (days for daily cadence, months for
    monthly, years for seasonal) and retries any that aren't COMPLETED yet -
    so an outage (Beat/worker down, a source that published late) is
    recovered automatically on the next tick, without operator intervention.
    Only the newest period is gated by a publish window (schedule_hour_utc/
    retry_until_hour_utc for daily; schedule_day_of_month/retry_window_days
    for monthly/seasonal); older periods are only throttled by
    retry_interval_minutes. See _candidate_run_dates.

    One static Beat entry polls frequently rather than one entry per workflow,
    so adding a new THREDDS source is an admin DB row, not a settings.py
    redeploy - matching the existing single "cleanup-wis2-downloads-daily"
    pattern.
    """
    now = timezone.now()

    for workflow in DownloadWorkflow.objects.filter(enabled=True):
        for run_date in _candidate_run_dates(workflow, now):
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
