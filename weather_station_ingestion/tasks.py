from __future__ import annotations

from celery import shared_task
from django.core.management import call_command


@shared_task(name="weather_station_ingestion.tasks.cleanup_wis2_downloads_task")
def cleanup_wis2_downloads_task() -> None:
    """Run retention-based cleanup for downloaded WIS2 payload files."""
    call_command("cleanup_wis2_downloads")

