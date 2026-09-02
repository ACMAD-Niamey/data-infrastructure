# THREDDS download & ingestion (`thredds_ingestion`)

Automates pulling dated products (daily forecasts, monthly/seasonal observed climatologies) from an ACMAD THREDDS file server and pushing them through the existing upload/ingest pipeline, so new dated STAC items keep appearing under datasets that are still created and styled the normal, manual way. Products are GeoTIFF already, or CSV converted to GeoTIFF on the way in - see [CSV-sourced products](#csv-sourced-products). The `cadence` field on a workflow controls how the scheduler steps `run_date` - see [Cadence](#cadence-daily-monthly-seasonal).

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
| `DownloadWorkflow` | One THREDDS source | `source_base_url`, `folder_pattern`, `cadence`, `schedule_hour_utc`/`schedule_minute_utc`, `retry_interval_minutes`, `retry_until_hour_utc`, `schedule_day_of_month`, `retry_window_days`, `anchor_month`, `publish_month_offset`, `catch_up_days` |
| `DownloadWorkflowFile` | One dataset + filename pattern mapped into a workflow (many per workflow) | `dataset` (FK to `catalog.DatasetPage`), `filename_pattern`, `lead_hours_csv`, `threshold_label`, `item_id_pattern`, `overwrite_existing`, `datetime_from_run_date`, `validity_hours`, `csv_value_column`, `csv_x_res`, `csv_y_res` |
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

### STAC datetime vs. filename lead: `datetime_from_run_date`

By default, a resolved item's STAC `datetime` (and `DownloadRunItem.valid_datetime`) is `run_date + lead_hours` — the date the forecast is *valid for*. For some products you instead want it queryable by the date the forecast was *issued* (e.g. "today's heat index outlook"), regardless of lead. Check `datetime_from_run_date` on the `DownloadWorkflowFile` row to pin the STAC datetime to `run_date` alone — `filename_pattern`/`item_id_pattern` are unaffected and still resolve using the real lead, so the file/item id stay correct and unique; only the STAC-queryable date changes.

### Products with a validity window: `validity_hours`

Some products don't represent an instant at all — a 5-day mean covers a period, not a point in time. Set `validity_hours` on the `DownloadWorkflowFile` row (e.g. `120` for 5 days) and the item is ingested with `start_datetime`/`end_datetime` instead of a single `datetime` — reusing the same fields the `ingest` API already uses for dekadal/seasonal cadence products (`ingest.tasks.build_item`). The window starts at whatever `valid_datetime` already resolves to (`run_date + lead_hours`, or `run_date` alone if `datetime_from_run_date` is also set) and ends `validity_hours` later. `DownloadRunItem.valid_end_datetime` records the window end for reference; it's blank for the common point-in-time case (`validity_hours` unset).

Example: a 5-day mean issued `2026-08-05`, `datetime_from_run_date=True`, `validity_hours=120` → STAC window `2026-08-05T00:00:00Z` to `2026-08-10T00:00:00Z`.

### Filenames with a date range: `{valid_end_date}`

Alongside `{valid_date}` (a single date), `{valid_end_date}` is available in any pattern once `validity_hours` is set on the `DownloadWorkflowFile` row — it's `{valid_date} + validity_hours`, formatted as a date. This is for products whose filename embeds a *range* rather than one date, e.g. `Vigilance_Data_GEFS_Week_1_Init-20260810_Valid-20260811-20260817.csv`. Referencing `{valid_end_date}` on a mapping with no `validity_hours` configured raises `PatternRenderError` at write time, the same way an unconfigured `{lead_hours}` does.

## Cadence: daily, monthly, seasonal

`DownloadWorkflow.cadence` controls how the Beat scheduler picks `run_date`s. It does **not** affect the management command (which always takes explicit dates), nor the pattern rendering — a `run_date` is a `run_date`.

| `cadence` | `run_date` meaning | Beat picks each tick | Publish-window gate on the newest period |
|---|---|---|---|
| `daily` (default) | the forecast issue day | today + previous `catch_up_days` days | `schedule_hour_utc` … `retry_until_hour_utc` (UTC time of day) |
| `monthly` | the 1st of the data month | last month + previous `catch_up_days` **months** | from day `schedule_day_of_month` of the *following* month, for `retry_window_days` days |
| `seasonal` | the 1st of the season's `anchor_month` | one run per year at `anchor_month` + previous `catch_up_days` **years** | from day `schedule_day_of_month` of month `anchor_month + publish_month_offset`, for `retry_window_days` days |

For `monthly`/`seasonal` the *current* period is never a target — its observed data doesn't exist until the period is over and the upstream batch has run (2–3 weeks later for the ACMAD OBS products). Older periods within `catch_up_days` are retried whenever they aren't `completed`, throttled only by `retry_interval_minutes` — same self-healing behaviour as daily catch-up.

### Locale-safe month tokens: `{month_abbr}` / `{month_name}`

Available in `folder_pattern`, `filename_pattern` and `item_id_pattern` alongside `{run_date}`. They render the **English** month for `run_date` (`Sep`, `September`) regardless of the host's `LC_TIME` locale — unlike `{run_date:%b}`, which would silently produce `sept.`/`Sept` on a non-English host and 404 every URL. Use them for products whose THREDDS path embeds the month name literally.

### Example: ACMAD monthly observed rainfall anomaly

`.../thredds/catalog/ACMAD/CDD/ClimateBulletin_TN/OBS_RAIN_ANOM/monthly/<Mon>/tif/AFR_<Mon>_<YYYY>_<Source>_<Var>.tif`
(`<Mon>` = `Jan`…`Dec`, `<Source>` ∈ `RFE2` / `CPC-UNI` / `CAMSO-PI`, `<Var>` ∈ `Tot` / `Tercile` / `Ranking_Percentile` / `Quintile` / `Precip-Anom` / `Pnorm` / `Percentile` / `Climo`).

**Workflow:**

| Field | Value |
|---|---|
| `source_base_url` | `https://sgbd.acmad.org/thredds/fileServer/ACMAD/CDD/ClimateBulletin_TN/OBS_RAIN_ANOM/monthly` |
| `folder_pattern` | `{month_abbr}/tif` |
| `cadence` | `monthly` |
| `schedule_day_of_month` | `12` (Sep 2025 landed 2025-10-17 — tune to the source's real lag) |

**One `DownloadWorkflowFile` per `(Source, Var)` you want as a dataset** (the linked `DatasetPage.cadence` must be `monthly`):

| Field | Value |
|---|---|
| `dataset` | e.g. `obs-rain-anom-rfe2` |
| `filename_pattern` | `AFR_{month_abbr}_{run_date:%Y}_RFE2_Precip-Anom.tif` |
| `lead_hours_csv` | *(blank)* |

Resolved item: `datetime` = `<YYYY>-<MM>-01T00:00:00Z`, `item_id` = `{dataset_id}_<YYYY><MM>01`, MinIO key `{dataset_id}/<YYYY>/<MM>/AFR_<Mon>_<YYYY>_RFE2_Precip-Anom.tif`.

### Example: ACMAD seasonal observed rainfall anomaly

`.../OBS_RAIN_ANOM/seasonal/<SEASON>/tif/AFR_<SEASON>_<YYYY>_<Source>_<Var>.tif`, where `<SEASON>` is a named rolling season (`DJF`, `MAM`, `JJA`, `SON`, `OND`, … also 4-/5-month and full-year combinations). The season **isn't derivable from a date**, so it's a literal in the patterns and there's **one workflow per season**:

| Field | Value (JJA) |
|---|---|
| `source_base_url` | `https://sgbd.acmad.org/thredds/fileServer/ACMAD/CDD/ClimateBulletin_TN/OBS_RAIN_ANOM/seasonal` |
| `folder_pattern` | `JJA/tif` |
| `cadence` | `seasonal` |
| `anchor_month` | `6` (June — first month of JJA; `SON`→9, `OND`→10, `DJF`→12) |
| `publish_month_offset` | `3` (data expected ~September; a 5-month season → ~5, a full-year one → ~13) |

`DownloadWorkflowFile` (linked `DatasetPage.cadence` = `seasonal`), one per `(Source, Var)`, with `validity_hours` set to the season length so the item is ingested as a `start_datetime`/`end_datetime` window:

| Field | Value |
|---|---|
| `filename_pattern` | `AFR_JJA_{run_date:%Y}_RFE2_Precip-Anom.tif` |
| `item_id_pattern` | `{dataset_id}_JJA_{run_date:%Y}` |
| `validity_hours` | `2208` (92 days: Jun 1 → Sep 1) |
| `lead_hours_csv` | *(blank)* |

### Backfill (monthly and seasonal)

```bash
# One period
python manage.py run_download_workflow --workflow-name "ACMAD OBS_RAIN_ANOM monthly" --run-month 2025-09
python manage.py run_download_workflow --workflow-name "ACMAD OBS_RAIN_ANOM JJA" --run-month 2025-06   # season anchor month

# Range - steps one calendar month at a time (not one day)
python manage.py run_download_workflow --workflow-id 5 --run-month-range 2000-01:2025-09 --dispatch-celery
```

`--run-month-range` over a seasonal workflow steps monthly, so ~11 of every 12 URLs it checks are 404s (cheap HEADs, and idempotency skips anything already done). For a deep seasonal backfill it's simpler to bump `catch_up_days` (interpreted as *years*) on the workflow for a few Beat ticks, then set it back.

## CSV-sourced products

Some THREDDS products publish a CSV of point values (`lon, lat, value`) instead of a raster — e.g. the Meningitis Vigilance GEFS series. The ingest pipeline only COG-optimizes `.tif`/`.tiff` keys (`ingest.cog.ensure_raster_is_cog`), so a downloaded `.csv` is automatically converted to a GeoTIFF before upload whenever `filename_pattern` renders to a `.csv` file — no extra flag needed to turn this on, but `csv_value_column` must be set to the name of the column holding raster values, or the item fails with a clear error instead of silently uploading garbage.

The conversion (`thredds_ingestion.services.raster_conversion.convert_to_raster`, wrapping `utils.raster_converstions.csv_to_raster`) uses fixed `x`/`y` columns (`"Data$x"`/`"y"`, matching every CSV product seen on this THREDDS source so far) and 0.5° grid resolution by default. Set `csv_x_res`/`csv_y_res` on the `DownloadWorkflowFile` row (degrees) only if a product's CSV grid uses a different spacing — leave both blank to keep the 0.5° default. `DownloadRunItem.filename` still records the original `.csv` name fetched from THREDDS (an audit trail of what was downloaded); only the MinIO key and uploaded asset become `.tif`.

The generated GeoTIFF also carries the linked dataset's `dataset_id`, `title`, `cadence`, and plain-text `description` (the same description shown in the catalog UI, via `catalog.ui_layers.dataset_description_payload`) as GeoTIFF tags — so the raster is self-describing even outside the STAC item, e.g. when opened directly in QGIS.

**Example**: the real two-week Vigilance product, one `DownloadWorkflowFile` row per week (the filename literally differs by `Week_1`/`Week_2`, so it can't be expressed as a single lead-hour series):

| Field | Week 1 | Week 2 |
|---|---|---|
| `dataset` | `meningitis-vigilance-gefs` | `meningitis-vigilance-gefs` |
| `filename_pattern` | `Vigilance_Data_GEFS_Week_1_Init-{run_date:%Y%m%d}_Valid-{valid_date:%Y%m%d}-{valid_end_date:%Y%m%d}.csv` | `Vigilance_Data_GEFS_Week_2_Init-{run_date:%Y%m%d}_Valid-{valid_date:%Y%m%d}-{valid_end_date:%Y%m%d}.csv` |
| `lead_hours_csv` | `24` | `192` |
| `validity_hours` | `144` | `144` |
| `csv_value_column` | `Vigilance` | `Vigilance` |
| `csv_x_res` / `csv_y_res` | *(blank — 0.5° grid)* | *(blank — 0.5° grid)* |

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

Each tick, for every enabled workflow, `run_due_download_workflows` builds the set of candidate `run_date`s per the [cadence table](#cadence-daily-monthly-seasonal), then dispatches each that isn't already `completed`/`running` and isn't inside its `retry_interval_minutes` throttle:

- **The newest period** (today / last month / this year's season) is gated by a publish window — `[schedule_hour_utc, retry_until_hour_utc]` UTC for daily; day `schedule_day_of_month` … `+ retry_window_days` for monthly/seasonal.
- **Older periods** within `catch_up_days` (days / months / years by cadence) are re-checked and retried if not yet `completed` — **not** gated by the publish window, only throttled by `retry_interval_minutes`.

This makes ongoing operation self-healing: if Beat/a worker was down, or a file published late, the backlog clears automatically on the next tick with no operator action. `catch_up_days` defaults to 3 and is meant for short gaps — for a deep historical backfill, use the management command instead of raising it (or, for monthly/seasonal where the period count is small, raise it briefly).

## Known infra quirk: ACMAD TLS

`sgbd.acmad.org` serves TLS with a Diffie-Hellman key considered too small by OpenSSL's default security policy (`DH_KEY_TOO_SMALL`). This is a server-side legacy TLS config, not something fixable on our end. `thredds_client.py` handles it transparently: a normal request is always tried first, and only on that specific SSL error does it retry once with a relaxed cipher policy (`SECLEVEL=1`) scoped to that single request — other hosts are unaffected and keep the stricter default.

## Related

- `docs/ingest-delete.md` — the upload/ingest pipeline this app calls into (reused, not duplicated).
- `ingest.tasks.process_ingestion_run` — COG conversion, bbox/geometry extraction, STAC item creation.
- `thredds_ingestion.services.raster_conversion` / `utils.raster_converstions.csv_to_raster` — the CSV→GeoTIFF conversion step, see [CSV-sourced products](#csv-sourced-products).
- `weather_station_ingestion` — the closest existing analog (a different external download pipeline, MQTT-based).
