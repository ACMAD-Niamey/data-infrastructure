# THREDDS download & ingestion (`thredds_ingestion`)

Automates pulling daily GeoTIFF forecast products from an ACMAD THREDDS file server and pushing them through the existing upload/ingest pipeline, so new dated STAC items keep appearing under datasets that are still created and styled the normal, manual way.

**What stays manual**: creating the `DatasetPage` and its `Layer` style snippet in Wagtail admin. This app never creates or edits either — it only references an existing `dataset_id`.

**What's automated**: resolving the dated THREDDS URL for a product, checking it exists, downloading it, uploading to MinIO, and calling the ingest pipeline (COG conversion, bbox/geometry extraction, STAC item creation) — all reused as-is from `uploads`/`ingest`, not duplicated.

## Prerequisites

Before configuring a workflow:

1. The target `DatasetPage` already exists (`catalog` app), with a stable `dataset_id`.
2. Its `Layer` style snippet already exists — styling is per-dataset, not per-item, so it applies automatically to every item this app ingests.

## Data model

One workflow represents one THREDDS **source** (shared base URL + dated-folder pattern + schedule); it can hold many product mappings, since a single ACMAD ensemble folder typically serves 20+ unrelated products under the same base URL.

| Model | Purpose | Key fields |
|---|---|---|
| `DownloadWorkflow` | One THREDDS source | `source_base_url`, `folder_pattern`, `schedule_hour_utc`/`schedule_minute_utc`, `retry_interval_minutes`, `retry_until_hour_utc`, `catch_up_days` |
| `DownloadWorkflowFile` | One dataset + filename pattern mapped into a workflow (many per workflow) | `dataset` (FK to `catalog.DatasetPage`), `filename_pattern`, `lead_hours_csv`, `threshold_label`, `item_id_pattern`, `overwrite_existing` |
| `DownloadRun` | One execution of a workflow for one `run_date` | `status` (`pending`/`running`/`completed`/`partial`/`failed`), per-run counters |
| `DownloadRunItem` | One resolved `(workflow_file, lead_hours)` file within a run | `source_url`, `item_id`, `status`, `ingestion_run_id` |

`lead_hours` uses `0` as a sentinel for "no lead-hour dimension" (single-file-per-day products like a 5-day mean) rather than `NULL`, since Postgres unique constraints treat `NULL != NULL` and would silently allow duplicates otherwise.

## Admin

Plain Django admin (not Wagtail) at `/api/django-admin/thredds_ingestion/` — these are operational config records, the same category as `ingest.IngestionRun`, not versioned page content.

Editing a `DownloadWorkflow` shows an inline formset of `DownloadWorkflowFile` rows underneath, so adding a new product from an already-configured source is just one more inline row, no new workflow.

### Example: adding a product to an existing source

Assume `ACMAD weather forecast` already exists as a workflow pointing at `.../ensemble5`, and a `5-day-cumulative-ukmo` `DatasetPage` + `Layer` already exist.

**Single-file-per-day product** (no lead hours):

| Field | Value |
|---|---|
| `dataset` | `5-day-cumulative-ukmo` |
| `filename_pattern` | `5daymean_{run_date:%Y%m%d}.tif` |
| `lead_hours_csv` | *(blank)* |

**Lead-hour product**:

| Field | Value |
|---|---|
| `dataset` | `mix6` |
| `filename_pattern` | `mix{run_date:%Y%m%d}_{lead_hours}.tif` |
| `lead_hours_csv` | `24,48,72,96,120,144` |

**Threshold + lead-hour product** (threshold is a literal, not a modeled variable — one workflow row per threshold):

| Field | Value |
|---|---|
| `dataset` | `wwfd_pop_50mm` |
| `filename_pattern` | `pop{run_date:%Y%m%d}_{threshold}_{lead_hours}.tif` |
| `threshold_label` | `50mm` |
| `lead_hours_csv` | `24,48,72,96,120,144` |

**Day-granularity product with the lead expressed as a second date**, not an hour count (e.g. `heat_index_20260806_20260809.tif` — same shape as the real `F_24hrPrecip_{run_date}_{valid_date}.nc` files on this THREDDS source):

| Field | Value |
|---|---|
| `dataset` | `heat_index` |
| `filename_pattern` | `heat_index_{run_date:%Y%m%d}_{valid_date:%Y%m%d}.tif` |
| `lead_hours_csv` | `0,24,48,72,96,120` |

`{valid_date}` is always available in any pattern — it's `run_date + lead_hours hours`, formatted as a date rather than a bare integer. It defaults to `run_date` itself when a mapping has no lead hours at all, so it's safe to use even on single-file-per-day products. Note `0` is a legitimate lead value here (a same-day/"day 0" forecast) and is treated as a real lead, not confused with "no lead-hour dimension" — that sentinel only applies when `lead_hours_csv` is left blank entirely.

## How `lead_hours_csv` drives the pattern

`lead_hours_csv` only ever holds hour offsets (`0,24,48,72,96,120`) — nothing date-shaped goes in that field. At run time, for **every** value in the list, the app automatically computes `lead_hours` hours added to whatever `run_date` it's currently processing, and substitutes both `{lead_hours}` and `{valid_date}` into `filename_pattern` (and `item_id_pattern`, if customized). One `DownloadRunItem` is resolved per `(workflow_file, lead_hours)` pair each run.

You never type out a resulting date or filename yourself — the same config produces the correct output for any `run_date`, including ones from a backfill:

| `run_date` | `lead_hours` | `{valid_date}` | resolved filename |
|---|---|---|---|
| 2026-08-06 | 0 | 2026-08-06 | `heat_index_20260806_20260806.tif` |
| 2026-08-06 | 24 | 2026-08-07 | `heat_index_20260806_20260807.tif` |
| 2026-08-06 | 72 | 2026-08-09 | `heat_index_20260806_20260809.tif` |
| 2026-08-07 | 72 | 2026-08-10 | `heat_index_20260807_20260810.tif` |

This is what makes a workflow keep working unattended day after day (and over an arbitrary backfill range) without ever touching its config again: `run_date` changes every day, `lead_hours_csv` stays fixed, and every placeholder that depends on either one is re-derived automatically for each run.

## Idempotency and retries

There is no dedup anywhere downstream — `ingest.tasks.post_item` does a bare POST with no existence check, so calling it twice with the same STAC item id either fails or silently overwrites depending on the STAC backend. This app owns 100% of the skip/retry logic itself, in this order, before any network call:

1. **DB fast path** — an existing `COMPLETED` item, not overwriting → skip.
2. **STAC reconciliation** — the item already exists in STAC (a prior run succeeded downstream but crashed before recording it locally) → skip.
3. **THREDDS existence check** — not published yet → `not_yet_available`. This is a normal, retriable state, not a failure (upstream files land in a daily batch, not instantly).
4. **Download → MinIO → ingest.**
5. **Downstream 409 reconciled as success** — if the ingest call fails with a duplicate-item-id conflict but the item is confirmed present in STAC, the item is marked completed rather than failed.

`item_id` is rendered per `(dataset, run_date, lead_hours)` and enforced globally unique at the DB level, so a misconfigured `item_id_pattern` (e.g. missing `{lead_hours}`) fails loudly at write time instead of surfacing as a STAC conflict days later.

## Running manually

```bash
# One workflow, one date
python manage.py run_download_workflow --workflow-name "ACMAD weather forecast" --run-date 2026-08-05

# Dry run - pattern rendering + THREDDS existence check only, no download/ingest
python manage.py run_download_workflow --workflow-id 3 --run-date 2026-08-05 --dry-run

# Force re-ingest even if already completed, for this invocation only
python manage.py run_download_workflow --workflow-id 3 --run-date 2026-08-05 --force
```

Reruns are always safe — already-completed items are skipped per the idempotency rules above, so a range can be re-run freely without duplicating work.

### Backfill

```bash
# Inclusive date range
python manage.py run_download_workflow --workflow-id 3 --run-date-range 2026-07-01:2026-08-05 --dispatch-celery

# Convenience: last N days through today
python manage.py run_download_workflow --all-enabled --days-back 14
```

Use `--dispatch-celery` for anything spanning more than a few dates - it fans out one task per `(workflow, run_date)` so workers process the backlog in parallel instead of downloading/converting/ingesting one date at a time inline.

## Running in production (Docker)

Production runs everything through Docker Compose, so `manage.py` commands go through the `web` container rather than a bare `python` invocation. `schedule_hour_utc` only gates the **Celery Beat** task (`run_due_download_workflows`) — it has no effect on the management command, so there's no need to touch a workflow's schedule to test it immediately instead of waiting for its scheduled hour.

SSH into the host first, then either form works (`docker compose exec` if your shell's `pwd` is the compose project directory; plain `docker exec <container_name>` otherwise — the container is named `geodatamanager_web` per `docker-compose.yml`):

```bash
# Dry run - confirm it resolves and the file is published, no side effects
docker exec geodatamanager_web python manage.py run_download_workflow \
  --workflow-name "<workflow name>" --run-date $(date -u +%Y-%m-%d) --dry-run

# Real run
docker exec geodatamanager_web python manage.py run_download_workflow \
  --workflow-name "<workflow name>" --run-date $(date -u +%Y-%m-%d)

# Backfill, dispatched to Celery workers
docker exec geodatamanager_web python manage.py run_download_workflow \
  --workflow-name "<workflow name>" --run-date-range 2026-07-01:2026-08-05 --dispatch-celery
```

Confirm results in admin at `/api/django-admin/thredds_ingestion/downloadrunitem/`, or `docker compose logs -f worker` while a `--dispatch-celery` backfill runs (a long historical range means real download/COG-conversion load on the worker).

## Scheduling (Celery Beat)

One static Beat entry (`run-due-thredds-download-workflows`, every 15 min) rather than one entry per workflow — adding a new THREDDS source is an admin DB row, not a settings.py redeploy.

Each tick, for every enabled workflow:

- **Today** is dispatched only inside `[schedule_hour_utc:schedule_minute_utc, retry_until_hour_utc]` UTC.
- The previous `catch_up_days` days are also re-checked and retried if not yet `completed` — **not** gated by time of day (a past day has no "time of day" left to wait for), only throttled by `retry_interval_minutes`.

This makes ongoing operation self-healing: if Beat/a worker was down for a day, or a file published late, the backlog clears automatically on the next tick with no operator action. `catch_up_days` defaults to 3 and is meant for short gaps — for a deep historical backfill (e.g. onboarding a product against a year of history), use the management command instead of raising it.

## Known infra quirk: ACMAD TLS

`sgbd.acmad.org` serves TLS with a Diffie-Hellman key considered too small by OpenSSL's default security policy (`DH_KEY_TOO_SMALL`). This is a server-side legacy TLS config, not something fixable on our end. `thredds_client.py` handles it transparently: a normal request is always tried first, and only on that specific SSL error does it retry once with a relaxed cipher policy (`SECLEVEL=1`) scoped to that single request — other hosts are unaffected and keep the stricter default.

## Related

- `docs/ingest-delete.md` — the upload/ingest pipeline this app calls into (reused, not duplicated).
- `ingest.tasks.process_ingestion_run` — COG conversion, bbox/geometry extraction, STAC item creation.
- `weather_station_ingestion` — the closest existing analog (a different external download pipeline, MQTT-based).
