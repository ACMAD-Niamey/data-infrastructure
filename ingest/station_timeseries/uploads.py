"""Shared "accept uploaded CSVs and queue a run" step for the API and the CMS."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from catalog.models import DatasetPage
from ingest.models import IngestionRun

RUN_KIND = "station_timeseries"
RUN_CADENCE = "station"  # IngestionRun.cadence has no meaning here; marks the run type
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ ()-]")


def _safe_name(name: str) -> str:
    return _SAFE_NAME.sub("_", os.path.basename(name))


def queue_station_timeseries_run(
    dataset: DatasetPage,
    files: Iterable[UploadedFile],
    *,
    group: str = "",
    commune: str = "",
) -> IngestionRun:
    """Persist the uploads under MEDIA_ROOT (shared by web and worker) and queue
    the Celery job. The files are kept after the run: they are the audit trail
    and let a failed run be retried or re-cleaned later."""
    from ingest.tasks import process_station_timeseries_run  # avoid import cycle

    run = IngestionRun.objects.create(
        dataset_id=dataset.dataset_id,
        cadence=RUN_CADENCE,
        status="accepted",
        payload={"kind": RUN_KIND, "files": [], "group": group, "commune": commune},
    )
    target_dir = Path(settings.MEDIA_ROOT) / "station_uploads" / f"run_{run.id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    stored: list[str] = []
    for upload in files:
        destination = target_dir / _safe_name(upload.name)
        with open(destination, "wb") as handle:
            for chunk in upload.chunks():
                handle.write(chunk)
        stored.append(str(destination))

    run.payload = {**run.payload, "files": stored}
    run.save(update_fields=["payload", "updated_at"])
    process_station_timeseries_run.delay(run.id)
    return run
