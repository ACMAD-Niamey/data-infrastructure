from __future__ import annotations

from celery import shared_task
from django.core.management import call_command


@shared_task(name="weather_station_ingestion.tasks.cleanup_wis2_downloads_task")
def cleanup_wis2_downloads_task() -> None:
    """Run retention-based cleanup for downloaded WIS2 payload files."""
    call_command("cleanup_wis2_downloads")


@shared_task(name="weather_station_ingestion.tasks.prune_wis2_raw_logs_task")
def prune_wis2_raw_logs_task() -> None:
    """Run retention-based deletion of RawPayloadLog DB rows (not just files)."""
    call_command("prune_wis2_raw_logs")

