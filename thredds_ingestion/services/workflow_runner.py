"""End-to-end run execution: idempotency/skip logic + download/upload/ingest.

There is no idempotency anywhere downstream (ingest.tasks.post_item does a
bare POST with no existence check), so every skip/dedup decision is owned
here, in this order, before any network call:

1. DB fast path       - existing COMPLETED item, not overwriting -> skip.
2. STAC recon fast path - item already exists in STAC (e.g. a prior run
   succeeded downstream but crashed before recording it locally) -> skip.
3. THREDDS existence check - not published yet is a normal, retriable state,
   not a failure.
4. Download -> MinIO put -> ingest.
5. A downstream 409 (duplicate STAC item id) is reconciled as success rather
   than treated as a hard failure, since the desired end state (item exists)
   is already achieved.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from . import ingest_bridge, raster_conversion, thredds_client
from .patterns import render_item_id, render_source_url, render_valid_datetime
from ..models import DownloadRun, DownloadRunItem, DownloadWorkflowFile

log = logging.getLogger(__name__)


def _stac_item_exists(dataset, item_id: str) -> bool:
    from ingest.stac_ops import get_stac_item

    # ingest.tasks.build_item/ensure_collection use dataset_id (not
    # stac_collection_id) as the STAC collection id - match that exactly.
    try:
        get_stac_item(dataset.dataset_id, item_id)
        return True
    except ValueError:
        return False


def _download_dir() -> Path:
    path = Path(getattr(settings, "THREDDS_DOWNLOAD_DIR", "/tmp/thredds_downloads"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def process_item(
    run: DownloadRun,
    workflow_file: DownloadWorkflowFile,
    lead_hours: int,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> DownloadRunItem:
    workflow = run.workflow
    dataset = workflow_file.dataset
    # lead_hours=0 is ambiguous on its own: it's both the sentinel for "this
    # workflow_file has no lead-hour dimension" (execute() passes 0 when
    # lead_hours_list() is empty) AND a legitimate configured lead (e.g. a
    # "day 0" forecast in an explicit "0,24,48,..." series). Disambiguate by
    # checking whether the workflow_file actually configures any lead hours,
    # not by checking the truthiness of the value itself.
    lh = lead_hours if workflow_file.lead_hours_list() else None

    source_url, filename = render_source_url(workflow, workflow_file, run.run_date, lh)
    item_id = render_item_id(workflow_file, dataset.dataset_id, run.run_date, lh)
    # filename/item_id always reflect the real lead (via lh above) - only the
    # STAC/valid_datetime can be pinned to the issue date instead, per
    # workflow_file.datetime_from_run_date.
    valid_dt = render_valid_datetime(run.run_date, None if workflow_file.datetime_from_run_date else lh)
    # A window (start_datetime/end_datetime) instead of a point-in-time
    # instant, for products like a 5-day mean - None for the common case.
    valid_end_dt = valid_dt + timedelta(hours=workflow_file.validity_hours) if workflow_file.validity_hours else None

    item, created = DownloadRunItem.objects.get_or_create(
        run=run,
        workflow_file=workflow_file,
        lead_hours=lead_hours,
        defaults={
            "filename": filename,
            "source_url": source_url,
            "item_id": item_id,
            "valid_datetime": valid_dt,
            "valid_end_datetime": valid_end_dt,
        },
    )
    overwrite = force or workflow_file.overwrite_existing

    # 1. DB fast path.
    if not created and item.status == DownloadRunItem.Status.COMPLETED and not overwrite:
        return item

    item.filename = filename
    item.source_url = source_url
    item.item_id = item_id
    item.valid_datetime = valid_dt
    item.valid_end_datetime = valid_end_dt

    # 2. STAC reconciliation fast path.
    if not overwrite and _stac_item_exists(dataset, item_id):
        item.status = DownloadRunItem.Status.SKIPPED
        item.error_message = "Reconciled: STAC item already exists."
        item.save()
        return item

    # 3. THREDDS existence check + 4. download/upload/ingest, all guarded -
    # any network/TLS error here (e.g. a partner server with weak/legacy TLS
    # params) is recorded on the item as a real failure, not left to crash
    # the whole run.
    local_path = _download_dir() / f"{item_id}_{filename}"
    upload_path = local_path
    try:
        available = thredds_client.exists(source_url, timeout=workflow.request_timeout_seconds)
        # A successful check this attempt supersedes any error recorded on a
        # previous failed attempt - don't leave stale error text on the item.
        item.error_message = ""
        if dry_run:
            item.status = DownloadRunItem.Status.PENDING if available else DownloadRunItem.Status.NOT_YET_AVAILABLE
            item.save()
            return item

        item.attempt_count += 1

        if not available:
            item.status = DownloadRunItem.Status.NOT_YET_AVAILABLE
            item.save()
            return item

        item.status = DownloadRunItem.Status.DOWNLOADING
        item.save()

        thredds_client.download_to_path(source_url, str(local_path), timeout=workflow.request_timeout_seconds)

        upload_filename = filename
        if local_path.suffix.lower() == ".csv":
            # THREDDS-published CSV (e.g. Meningitis Vigilance GEFS) - convert
            # to a GeoTIFF before upload, since only .tif/.tiff keys get
            # COG-optimized downstream (ingest.cog.ensure_raster_is_cog).
            upload_path = raster_conversion.convert_to_raster(local_path, workflow_file, _download_dir())
            upload_filename = upload_path.name

        key = ingest_bridge.build_minio_key(dataset.dataset_id, run.run_date, upload_filename)
        href = ingest_bridge.upload_file(str(upload_path), key=key)
        item.minio_href = href

        item.status = DownloadRunItem.Status.INGESTING
        item.save()

        # 4. Download -> MinIO put -> ingest (above), synchronous ingest call below.
        ingestion_run = ingest_bridge.push_to_ingest(
            dataset=dataset, href=href, item_id=item_id, valid_datetime=valid_dt, valid_end_datetime=valid_end_dt
        )
        item.ingestion_run_id = ingestion_run.id

        if ingestion_run.status == "completed":
            item.status = DownloadRunItem.Status.COMPLETED
            item.error_message = ""
        elif "409" in (ingestion_run.error_message or "") and _stac_item_exists(dataset, item_id):
            # 5. Downstream conflict, but the item is actually present - reconcile as success.
            item.status = DownloadRunItem.Status.COMPLETED
            item.error_message = f"Reconciled after downstream conflict: {ingestion_run.error_message}"
        else:
            item.status = DownloadRunItem.Status.FAILED
            item.error_message = ingestion_run.error_message
    except Exception as exc:  # noqa: BLE001 - recorded on the item, not swallowed
        item.status = DownloadRunItem.Status.FAILED
        item.error_message = str(exc)
        log.exception("thredds_ingestion item failed: item_id=%s", item_id)
    finally:
        if not getattr(settings, "THREDDS_KEEP_DOWNLOADED_FILES", False):
            for path in {local_path, upload_path}:
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
        item.save()

    return item


def execute(run: DownloadRun, *, force: bool = False, dry_run: bool = False) -> DownloadRun:
    workflow = run.workflow
    run.status = DownloadRun.Status.RUNNING
    if not run.started_at:
        run.started_at = timezone.now()
    run.last_attempted_at = timezone.now()
    run.attempt_count += 1
    run.save()

    pairs: list[tuple[DownloadWorkflowFile, int]] = []
    for workflow_file in workflow.files.filter(enabled=True).order_by("sort_order", "id"):
        lead_hours_list = workflow_file.lead_hours_list()
        if lead_hours_list:
            pairs.extend((workflow_file, lh) for lh in lead_hours_list)
        else:
            pairs.append((workflow_file, 0))

    total = completed = failed = not_yet_available = 0
    for workflow_file, lead_hours in pairs:
        item = process_item(run, workflow_file, lead_hours, force=force, dry_run=dry_run)
        total += 1
        if item.status in (DownloadRunItem.Status.COMPLETED, DownloadRunItem.Status.SKIPPED):
            completed += 1
        elif item.status == DownloadRunItem.Status.NOT_YET_AVAILABLE:
            not_yet_available += 1
        elif item.status == DownloadRunItem.Status.FAILED:
            failed += 1

    run.total_files = total
    run.completed_files = completed
    run.failed_files = failed
    run.not_yet_available_files = not_yet_available

    if dry_run:
        run.status = DownloadRun.Status.PENDING
    elif not_yet_available > 0:
        run.status = DownloadRun.Status.PARTIAL
    elif failed > 0:
        run.status = DownloadRun.Status.FAILED if completed == 0 else DownloadRun.Status.PARTIAL
    else:
        run.status = DownloadRun.Status.COMPLETED
        run.finished_at = timezone.now()

    run.save()
    return run
