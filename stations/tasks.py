"""Celery tasks for the stations app."""

from __future__ import annotations

import logging

import requests
from celery import shared_task

from stations.models import Station
from stations.services.isd_lite_importer import ISDLiteImporter

log = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
)
def ingest_isd_lite_year(self, station_id: int, year: int) -> dict:
    """Backfill one (station, year) of NOAA ISD-Lite hourly observations.

    Idempotent: re-runs return ``written=0`` because of the
    ``observations`` PK and ``bulk_create(ignore_conflicts=True)``.
    """
    station = Station.objects.get(pk=station_id)
    return ISDLiteImporter().import_year(station=station, year=year).as_dict()
