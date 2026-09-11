from __future__ import annotations

from celery import shared_task
from django.core.management import call_command


@shared_task(name="weather_station_ingestion.tasks.cleanup_wis2_downloads_task")
def cleanup_wis2_downloads_task() -> None:
    """Run retention-based cleanup for downloaded WIS2 payload files."""
    call_command("cleanup_wis2_downloads")


@shared_task(name="weather_station_ingestion.tasks.prune_wis2_raw_logs_task")
def prune_wis2_raw_logs_task(
    older_than_days: int | None = None,
    batch_size: int | None = None,
    statuses: list[str] | None = None,
    dry_run: bool = False,
) -> None:
    """Run retention-based deletion of RawPayloadLog DB rows (not just files).

    The daily beat schedule calls this with no args (settings defaults —
    small day-to-day deltas once caught up). For a one-off backlog catch-up,
    trigger it manually with a larger batch_size so it doesn't have to be run
    from a blocking foreground shell:

        docker compose exec web python manage.py shell -c "
        from weather_station_ingestion.tasks import prune_wis2_raw_logs_task
        prune_wis2_raw_logs_task.delay(batch_size=50000)
        "

    Progress/result land in the worker's own log (`docker compose logs -f
    worker`), not the caller's terminal.
    """
    kwargs = {"dry_run": dry_run}
    if older_than_days is not None:
        kwargs["older_than_days"] = older_than_days
    if batch_size is not None:
        kwargs["batch_size"] = batch_size
    if statuses is not None:
        kwargs["status"] = statuses
    call_command("prune_wis2_raw_logs", **kwargs)

