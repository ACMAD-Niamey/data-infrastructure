# GeoDataManager

A Django-based geospatial data management system for multi-hazard data: weather stations, raster datasets, STAC catalog, and an MCP-powered AI assistant layer that lets LLMs query real data without hallucination.

## Project Overview

GeoDataManager provides the data infrastructure for ACMAD's multi-hazard platform. It includes:

- **Catalog Management**: Wagtail-managed layers (GeoServer WMS, static tiles, STAC rasters) with legend and styling
- **STAC Raster Catalog**: Ingest and serve Cloud-Optimized GeoTIFFs via pgSTAC + STAC FastAPI + TiTiler
- **Stations & Observations**: Weather station metadata, timeseries storage, WIS2/MQTT ingestion
- **Vector Tile Service**: OGC API – Features/Tiles via TiPG over PostGIS
- **GeoOracle MCP Server**: Model Context Protocol server exposing catalog, STAC, stations, observations, and country-level zonal statistics as AI tools
- **Async Processing**: Celery + Redis for ingestion jobs and scheduled tasks
- **Cloud Storage**: MinIO (S3-compatible) for raster assets
- **Multi-hazard UI**: React/Vite frontend at `multi-hazard.acmad.org`

## Tech Stack

- **Backend**: Django 5.2+ with Django REST Framework
- **CMS**: Wagtail 7.2+ — layer config, legend, styling, MCP server registry, LLM provider config
- **Database**: PostgreSQL + PostGIS (`geodatamanager`) + pgSTAC (separate instance for STAC metadata)
- **Raster catalog**: STAC FastAPI (pgstac) + TiTiler (COG tile serving)
- **Vector tiles**: TiPG (OGC API – Tiles from PostGIS)
- **Task Queue**: Celery + Redis
- **Object Storage**: MinIO
- **MCP server**: GeoOracle — FastMCP 3.x, SSE transport, 17 tools across catalog/STAC/stations/observations/countries/zonal-stats
- **AI (planned)**: Anthropic Claude via `assistant` Django app — chat endpoint + MCP registry
- **Web Server**: Gunicorn + Nginx
- **Containerization**: Docker Compose (15 services)

## Documentation

- **[Architecture](docs/architecture.md)** — system diagram, service responsibilities, data-flow principles
- **[Roadmap](docs/roadmap.md)** — multi-hazard platform evolution, MCP/LLM status
- **[Ingest & delete API](docs/ingest-delete.md)** — STAC raster ingest pipeline

## Project Structure

```
geomgr/
├── docs/                        # Architecture & roadmap
├── catalog/                     # Layer catalog (Wagtail snippets, availability, visualization)
├── ingest/                      # STAC raster ingest/delete API + Celery tasks
├── stations/                    # Weather station metadata + country boundaries
├── observations/                # Timeseries observations + aggregation queries
├── sources/                     # Data source metadata
├── weather_station_ingestion/   # WIS2/MQTT consumer + cleanup
├── uploads/                     # File upload presign + status tracking
├── vector_ingest/               # Vector data ingest jobs
├── home/                        # Wagtail homepage
├── search/                      # Wagtail search
├── assistant/                   # (planned) AI chat endpoint + MCP registry + LLM config
├── mcp/                         # GeoOracle MCP server (FastMCP, SSE transport)
│   ├── server.py                #   FastMCP entry point
│   ├── client.py                #   Shared httpx clients
│   ├── cache.py                 #   Redis cache for zonal stats
│   └── tools/                   #   17 tools: catalog, stac, stations, observations, countries, zonal_stats
├── multi-hazard-ui/             # React/Vite multi-hazard dashboard
├── afri-met/                    # React/MapLibre station map (Afri-Met)
├── e-safari-ui/                 # Shared React component library
├── geodatamanager/              # Django project config
│   ├── settings/base.py
│   ├── urls.py
│   └── celery.py
├── nginx/                       # Nginx configs (default.conf, default_ssl.conf)
├── docker-compose.yml           # 15-service orchestration
├── Makefile                     # Development shortcuts
└── requirements.txt
```

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- PostgreSQL 13+ with PostGIS extension (in Docker)
- Redis (in Docker)
- MinIO (in Docker)

## Installation & Setup

### Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ACMAD-Niamey/data-infrastructure.git
   cd geomgr
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   ```
   Configure the following variables in `.env`:
   - `POSTGRES_PASSWORD`: Database password
   - `POSTGRES_USER`: Database user (default: geodatamanager)
   - `POSTGRES_DB`: Database name (default: geodatamanager)
   - `DEBUG`: Set to False in production
   - `SECRET_KEY`: Django secret key
   - `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

3. **Build and start services**:
   ```bash
   make build
   ```

4. **Run migrations**:
   ```bash
   make migrate
   ```

5. **Create superuser**:
   ```bash
   make createsuperuser
   ```

6. **Collect static files**:
   ```bash
   make collectstatic
   ```

### Local Development Setup

1. **Create virtual environment**:
   ```bash
   python3 -m venv venv_geo
   source venv_geo/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up database** (requires PostgreSQL with PostGIS):
   ```bash
   python manage.py migrate
   ```

4. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

5. **Run development server**:
   ```bash
   python manage.py runserver
   ```

## Common Commands

### Docker Compose

```bash
make build              # Build and start all services
make up                 # Start services
make down               # Stop and remove services
make logs               # View service logs
make makemigrations     # Create database migrations
make migrate            # Apply migrations
make createsuperuser    # Create admin user
make collectstatic      # Collect static files
make shell              # Access Django shell
make connectdb          # Connect to database with psql
```

### Django Management

```bash
python manage.py runserver           # Run development server
python manage.py makemigrations       # Create migrations
python manage.py migrate              # Apply migrations
python manage.py createsuperuser      # Create superuser
python manage.py collectstatic        # Collect static files
python manage.py shell                # Interactive shell
```

### Celery

```bash
celery -A geodatamanager worker -l info    # Start Celery worker
celery -A geodatamanager beat              # Start Celery beat scheduler
```

## API Documentation

### Development Environment

- **Swagger UI**: http://localhost:8000/api/schema/swagger-ui/
- **ReDoc**: http://localhost:8000/api/schema/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### Production Environment (via Nginx)

In production, only ports 80 (HTTP) and 443 (HTTPS) are exposed through Nginx reverse proxy:

- **Swagger UI**: https://yourdomain.com/api/schema/swagger-ui/
- **ReDoc**: https://yourdomain.com/api/schema/redoc/
- **OpenAPI Schema**: https://yourdomain.com/api/schema/

All service endpoints (Django, TiPG, etc.) are accessed through the Nginx reverse proxy on standard ports.

## Services

The application runs multiple services in Docker:

### Services

All 15 services run on `data_infra_network`. Only nginx exposes public ports (80/443).

| Service | Internal | Public path | Purpose |
|---------|----------|-------------|---------|
| `web` | 8070 | `/api/` | Django REST API, Wagtail admin |
| `nginx` | 80, 443 | — | Reverse proxy, TLS, static files |
| `db` | 5432 | — | PostgreSQL + PostGIS (main app data) |
| `pgstac` | 5432 | — | PostgreSQL for STAC metadata (separate instance) |
| `redis` | 6379 | — | Celery broker + cache |
| `minio` | 9000/9001 | `minio.acmad.org`, `console-minio.acmad.org` | Object storage (rasters, archives) |
| `worker` | — | — | Celery background worker |
| `celery-beat` | — | — | Scheduled tasks (WIS2 cleanup, etc.) |
| `wis2_consumer` | — | — | MQTT broker consumer for live station data |
| `tipg` | 8080 | `/tipg/` | OGC API – Tiles / vector tiles from PostGIS |
| `stac_api` | 8080 | `/stac/` | STAC FastAPI (raster catalog, transactions) |
| `titiler` | 80 | `/titiler/` | COG raster tile serving |
| `pgstac_migrate` | — | — | One-off pgSTAC schema init |
| `mcp` | 8090 | `/mcp/` | GeoOracle MCP server (SSE transport) |
| `certbot` | — | — | Let's Encrypt SSL management |

## GeoOracle MCP Server

**GeoOracle** is the Model Context Protocol server that exposes GeoDataManager's capabilities as AI tools. It runs as a standalone Python service (`mcp/`) using FastMCP 3.x with SSE transport.

### Tools (17 total)

| Module | Tools |
|--------|-------|
| `catalog` | `list_hazard_categories`, `list_catalog_layers`, `get_dataset_availability`, `get_dataset_visualization` |
| `stac` | `list_stac_collections`, `get_stac_collection`, `search_stac_items` |
| `stations` | `search_stations`, `get_station_detail`, `get_station_stats`, `get_station_facets` |
| `observations` | `get_latest_observations`, `get_observation_stats` |
| `countries` | `resolve_country` (name → ISO alpha-3 code + bounds), `list_countries` |
| `zonal_stats` | `get_country_raster_stats` (single date), `get_country_raster_timeseries` (date range, Redis-cached) |

### Endpoints

| Transport | URL | Use case |
|-----------|-----|----------|
| SSE (deployed) | `https://multi-hazard.acmad.org/mcp/sse` | Remote MCP clients, chatbot backend |
| SSE (local) | `http://localhost/mcp/sse` | Local development |
| stdio (dev) | `docker compose run --rm -T --no-deps -e MCP_TRANSPORT=stdio mcp` | Claude Code direct |

### Connecting Claude Code

Add to your Claude Code MCP settings:
```json
{
  "mcpServers": {
    "geomgr-remote": { "url": "https://multi-hazard.acmad.org/mcp/sse" }
  }
}
```

Or use the project `.mcp.json` at the repo root which includes both local and remote entries.

### Zonal statistics chain

The `get_country_raster_stats` and `get_country_raster_timeseries` tools chain three services:
```
1. Django  → GET /api/stations/country-boundary/{code}/   (full GeoJSON polygon)
2. STAC    → POST /stac/search  (find raster asset for date range)
3. TiTiler → POST /cog/statistics?url={s3_href}  (compute stats masked by polygon)
```
Results are cached in Redis (`zonal:{dataset}:{country}:{date}`, 24h TTL).

### Environment variables (mcp service)

```bash
DJANGO_API_URL=http://web:8070
STAC_API_URL=http://stac_api:8080
TITILER_URL=http://titiler:80
TIPG_URL=http://tipg:8080
REDIS_URL=redis://redis:6379/1
MCP_TRANSPORT=sse          # sse (deployed) or stdio (local dev override)
MCP_PORT=8090
```

---

## AI Assistant (planned)

A `POST /api/assistant/chat/` endpoint is planned under the `assistant` Django app. It will:

1. Load the configured LLM provider (Claude or OpenAI) from Wagtail admin → **Snippets → LLM providers**
2. Load all active MCP servers from Wagtail admin → **Snippets → MCP servers**
3. Connect to each MCP server, fetch its tool list
4. Run the agentic tool-calling loop via the Anthropic SDK
5. Return the grounded text response

External MCP servers (beyond GeoOracle) can be registered in Wagtail admin with URL + optional auth token — no code change needed to extend the assistant's capabilities.

Required environment variables (when implemented):
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Environment Variables

Key environment variables (see `.env` or `.env.example`):

```bash
# Django
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (main)
POSTGRES_USER=geodatamanager
POSTGRES_PASSWORD=your-password
POSTGRES_DB=geodatamanager
POSTGRES_HOST=db
POSTGRES_PORT=5432

# pgSTAC database (separate instance)
PG_STAC_POSTGRES_USER=pgstac
PG_STAC_POSTGRES_PASSWORD=your-pgstac-password
PG_STAC_POSTGRES_DB=pgstac
PG_STAC_POSTGRES_HOST=pgstac

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000

# Redis
REDIS_URL=redis://redis:6379/0

# Storage
STATIC_VOLUME=/home/app/web/static
MEDIA_VOLUME=/app/media

# TiPG
TIPG_DEBUG=false

# GeoOracle MCP server
MCP_TRANSPORT=sse
MCP_PORT=8090

# AI assistant (add when implementing the assistant app)
ANTHROPIC_API_KEY=sk-ant-...
```

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test**:
   ```bash
   python manage.py test          # Run tests
   make logs                      # Monitor logs
   ```

3. **Format and lint** (if configured):
   ```bash
   black .                        # Format code
   flake8 .                       # Lint
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

5. **Create a pull request** on GitHub

## Database Schema

The project uses Django ORM with the following main models:

- **Catalog**: Layer management and metadata (Wagtail **Layer** snippets: color stops and **legend** use swatch + `#RRGGBB` editors; label→color legend maps match e-safari-ui; QML/SLD import still supported)
- **Ingest**: STAC raster ingest/delete jobs and tracking ([ingest & delete API](docs/ingest-delete.md))
- **Uploads**: File upload handling
- **VectorIngest**: Vector-specific processing

Migrations are located in each app's `migrations/` directory.

## Migrating Stations Between Environments

Locally-enriched stations (e.g. NOAA-imported with country/admin1/admin2 already filled
in via Nominatim) can be copied into another environment without re-hitting any
external API. Two management commands implement this:

- `dump_stations_to_json <output.ndjson>` — serialize stations to NDJSON. Geometry
  is exported as WKT. `id` is intentionally omitted so the destination assigns its
  own primary keys. Optional flags: `--station-type synop` (repeatable),
  `--only-missing-canonical`, `--limit N`.
- `load_stations_from_json <input.ndjson>` — idempotent insert via
  `bulk_create(ignore_conflicts=True)`. Conflicts on the unique `station_code`
  column are silently skipped, so re-running is a safe no-op. Optional flags:
  `--batch-size N` (default 500), `--dry-run`.

Scope: only the `stations` table is moved. Aliases, sensors, and observations are
not touched (aliases/sensors are recreated by MQTT ingestion on first message).
No Nominatim or other HTTP calls happen during load — all enrichment values
(`country_name`, `admin1`, `admin2`, `canonical_code`) are written verbatim.

End-to-end workflow (local -> prod):

```bash
# 1) Local
docker compose exec web python manage.py dump_stations_to_json /tmp/stations_export.ndjson
docker compose cp web:/tmp/stations_export.ndjson ./stations_export.ndjson

# 2) Ship to prod
scp -P 2224 ./stations_export.ndjson linuxuser@<prod-host>:/tmp/

# 3) On prod
docker compose cp /tmp/stations_export.ndjson web:/tmp/stations_export.ndjson
docker compose exec web python manage.py load_stations_from_json /tmp/stations_export.ndjson --dry-run
docker compose exec web python manage.py load_stations_from_json /tmp/stations_export.ndjson

# 4) Reconcile canonical_code from country_boundaries (DB-only, no Nominatim)
docker compose exec web python manage.py sync_station_canonical_code
```

Both source and destination must be on the same migration set
(at least `stations.0009_widen_country_codes`).

## Backfilling Historical NOAA ISD-Lite Observations

Hourly historical observations from the NOAA Integrated Surface Database
(ISD-Lite subset) can be loaded into the `observations` hypertable for any
station that already exists locally. The ingest is **idempotent** thanks to the
observations primary key `(station_id, variable_code, observed_at)` plus
`bulk_create(ignore_conflicts=True)` -- safe to re-run.

### Prerequisites

- The target stations must exist. Run `python manage.py import_wmo_stations`
  first if you don't have NOAA stations yet.
- The host running the command needs outbound HTTPS to
  `https://www.ncei.noaa.gov`.

### Variables ingested

ISD-Lite -> internal `Observation.variable_code`:

| ISD-Lite column | Internal code     | Unit | Notes                      |
| --------------- | ----------------- | ---- | -------------------------- |
| `temp`          | `temp`            | degC | scaled / 10                |
| `slp`           | `pressure`        | hPa  | scaled / 10                |
| `wdir`          | `wind_direction`  | deg  |                            |
| `wspd`          | `wind_speed`      | m/s  | scaled / 10                |
| `prcp_1h`       | `rainfall`        | mm   | scaled / 10; trace -> 0.0  |

`dewp`, `skyc`, and `prcp_6h` are intentionally skipped. Every row is tagged
`qc_flag = 'noaa_isd_lite'` for easy querying or rollback.

### Command

```bash
python manage.py ingest_noaa_isd_lite [--year YYYY | --years YYYY:YYYY] \
    [--station-code 60001 ... | --africa-only] \
    [--dispatch-celery] [--dry-run]
```

Flag reference:

- `--year` / `--years` (required, mutually exclusive): single year or inclusive range.
- `--station-code` (repeatable) or `--africa-only`: which stations to backfill.
  Default if neither is given is `--africa-only` (WMO blocks 60-69).
- `--dispatch-celery`: enqueue one Celery task per (station, year) instead of
  running inline. Mutually exclusive with `--dry-run`.
- `--dry-run`: fetch + parse + count, no DB writes.

### Examples

```bash
# Smoke test: one station, one year, no writes
docker compose exec web python manage.py ingest_noaa_isd_lite \
    --year 2023 --station-code 60001 --dry-run

# Real insert
docker compose exec web python manage.py ingest_noaa_isd_lite \
    --year 2023 --station-code 60001

# Bulk African backfill via Celery (recommended for multi-year jobs)
docker compose exec web python manage.py ingest_noaa_isd_lite \
    --years 2020:2024 --africa-only --dispatch-celery
```

Per-station output looks like:

```
station=60001 year=2023 parsed=28537 written=28537 skipped_existing=0 error=-
```

On a second run for the same `(station, year)`, `written=0` and
`skipped_existing` accounts for everything already in the DB.

### Verification

```sql
-- Coverage per station/year/variable
SELECT s.station_code,
       EXTRACT(YEAR FROM o.observed_at)::int AS year,
       o.variable_code,
       COUNT(*) AS rows,
       MIN(o.observed_at) AS first_obs,
       MAX(o.observed_at) AS last_obs
FROM observations o
JOIN stations s ON s.id = o.station_id
WHERE o.qc_flag = 'noaa_isd_lite'
GROUP BY s.station_code, year, o.variable_code
ORDER BY s.station_code, year, o.variable_code;

-- Total NOAA ISD-Lite rows (should be stable across re-runs)
SELECT COUNT(*) FROM observations WHERE qc_flag = 'noaa_isd_lite';
```

To roll back a backfill cohort entirely:

```sql
DELETE FROM observations WHERE qc_flag = 'noaa_isd_lite';
```

## WIS2 Download Retention Cleanup

Downloaded WIS2/MQTT payload files can be cleaned up with a retention policy.
Default retention is **7 days**, configurable to a shorter or longer window.

### Defaults and configuration

- Default retention: `WIS2_DOWNLOAD_RETENTION_DAYS=7`
- Override globally via env var:
  - `WIS2_DOWNLOAD_RETENTION_DAYS=<days>`
- Override per-run via command:
  - `--older-than-days <days>`

### Safety rules

Cleanup only targets rows where:
- `processing_status IN (processed, skipped, failed)`
- `received_at <= now - retention`
- `local_file_path` is non-null/non-empty

It does **not** touch pending/downloading logs.

### Command usage

```bash
# Use default retention from settings/env (7 days by default)
docker compose exec web python manage.py cleanup_wis2_downloads

# Override retention for this run
docker compose exec web python manage.py cleanup_wis2_downloads --older-than-days 3

# Preview only (no file/DB changes)
docker compose exec web python manage.py cleanup_wis2_downloads --dry-run
```

Invalid retention (`<= 0`) is rejected.

### Output summary

Each run prints:
- `cutoff`: computed retention cutoff timestamp
- `scanned`: candidate log rows evaluated
- `deleted`: files successfully removed
- `missing`: file paths that no longer existed on disk
- `failed`: unlink failures
- `paths_cleared`: DB rows whose `local_file_path` was nulled

### Scheduling

A daily Celery Beat schedule is configured to run at **03:00 UTC** using:
- task: `weather_station_ingestion.tasks.cleanup_wis2_downloads_task`

Make sure `celery beat` is running in the target environment; otherwise cleanup
will only run when invoked manually.

## Testing

Run tests with:

```bash
python manage.py test                    # Run all tests
python manage.py test catalog            # Run app-specific tests
python manage.py test catalog.tests.ModelTests  # Run specific test class
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in settings
- [ ] Configure `SECRET_KEY` securely
- [ ] Set `ALLOWED_HOSTS` properly
- [ ] Use strong database password
- [ ] Enable HTTPS/SSL (certbot + Let's Encrypt)
- [ ] Set `ANTHROPIC_API_KEY` for AI assistant
- [ ] Configure `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`
- [ ] Set `PG_STAC_POSTGRES_PASSWORD`
- [ ] Set up proper logging
- [ ] Configure backup strategy
- [ ] Run migrations on fresh database
- [ ] Collect static files
- [ ] Verify GeoOracle MCP responds at `/mcp/sse`
- [ ] Set up monitoring & alerts

### Production Deployment

```bash
# Using docker-compose
docker-compose -f docker-compose.yml up -d

# Or with production settings
DJANGO_SETTINGS_MODULE=geodatamanager.settings.production python manage.py migrate
DJANGO_SETTINGS_MODULE=geodatamanager.settings.production python manage.py collectstatic --noinput
```

## Troubleshooting

### Database Connection Issues
```bash
# Check database connectivity
make connectdb

# Reset database (warning: deletes all data)
docker-compose down -v
docker-compose up -d
make migrate
```

### Static Files Not Loading
```bash
make collectstatic
```

### Celery Tasks Not Processing
```bash
# Check Redis connectivity
docker-compose logs redis

# Restart worker
docker-compose restart worker
```

### Port Already in Use
```bash
# Change ports in docker-compose.yml or .env
# Or kill existing process on the port
lsof -i :8000
kill -9 <PID>
```

## Stations & Observations API

The Stations API provides read-only access to weather station metadata and observation time-series. All queries use raw SQL (no ORM) and are served under `/api/stations/`.

### Endpoints overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/stations/` | List all active stations that have observations |
| `GET` | `/api/stations/<station_code>/` | Station detail + per-variable record counts |
| `GET` | `/api/stations/<station_code>/stats/` | Time-series aggregation for one variable |

Full interactive documentation (try-it-out) is available at `/api/docs/` under the **Stations** tag.

---

### `GET /api/stations/`

Returns all active stations that have at least one observation.

**Response**
```json
{
  "count": 40,
  "results": [
    {
      "id": 99,
      "station_code": "60390",
      "name": "DAR-EL-BEIDA",
      "country_code": "DZA",
      "station_type": "aws",
      "elevation_m": 25.0,
      "latitude": 36.69,
      "longitude": 3.22,
      "variables_available": ["dewpoint", "pressure", "rh", "temp", "wind_speed"],
      "latest_observed_at": "2026-04-27T07:00:00Z"
    }
  ]
}
```

---

### `GET /api/stations/<station_code>/`

Returns metadata for a single station plus per-variable record counts.

**Path parameter**: `station_code` — e.g. `60390` or `WIGOS_0_20000_0_60401`

**Response**
```json
{
  "id": 99,
  "station_code": "60390",
  "name": "DAR-EL-BEIDA",
  "country_code": "DZA",
  "station_type": "aws",
  "is_active": true,
  "elevation_m": 25.0,
  "latitude": 36.69,
  "longitude": 3.22,
  "total_records": 8,
  "first_observation": "2026-04-27T07:00:00Z",
  "last_observation": "2026-04-27T07:00:00Z",
  "variables": [
    {
      "variable_code": "temp",
      "unit": "degC",
      "record_count": 1,
      "first_observation": "2026-04-27T07:00:00Z",
      "last_observation": "2026-04-27T07:00:00Z"
    }
  ]
}
```

Returns `404` if the station code is not found.

---

### `GET /api/stations/<station_code>/stats/`

Returns aggregated or raw time-series for a single variable at a station.

**Path parameter**: `station_code`

**Query parameters**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `variable` | Yes | — | Variable code: `temp`, `dewpoint`, `rh`, `pressure`, `wind_speed`, `wind_direction`, `rainfall`, `visibility`, `elevation` |
| `agg` | No | `daily` | Aggregation level: `raw`, `hourly`, `daily`, `monthly`, `yearly` |
| `start` | No | 30 days ago | Start date inclusive, ISO 8601 (e.g. `2026-04-01`) |
| `end` | No | today | End date inclusive, ISO 8601 (e.g. `2026-04-27`) |

**Aggregated response** (`agg=hourly|daily|monthly|yearly`)
```json
{
  "station_code": "60390",
  "station_name": "DAR-EL-BEIDA",
  "variable": "temp",
  "aggregation": "daily",
  "start": "2026-04-01",
  "end": "2026-04-27",
  "data": [
    {
      "period": "2026-04-27T00:00:00Z",
      "avg": 18.1,
      "min": 14.2,
      "max": 24.8,
      "count": 4
    }
  ]
}
```

**Raw response** (`agg=raw`, capped at 5 000 rows)
```json
{
  "station_code": "60390",
  "station_name": "DAR-EL-BEIDA",
  "variable": "temp",
  "aggregation": "raw",
  "start": "2026-04-01",
  "end": "2026-04-27",
  "data": [
    {
      "period": "2026-04-27T07:00:00Z",
      "value": 18.1,
      "unit": "degC"
    }
  ]
}
```

> **Note:** Pressure values stored internally in Pa are automatically normalised to hPa in all responses.

---

### Example requests

```bash
# List all stations
curl http://localhost/api/stations/

# Station detail
curl http://localhost/api/stations/60390/

# Daily temperature for April 2026
curl "http://localhost/api/stations/60390/stats/?variable=temp&agg=daily&start=2026-04-01&end=2026-04-30"

# Raw pressure readings (last 30 days, default window)
curl "http://localhost/api/stations/60390/stats/?variable=pressure&agg=raw"

# Monthly wind speed for a full year
curl "http://localhost/api/stations/60390/stats/?variable=wind_speed&agg=monthly&start=2026-01-01&end=2026-12-31"
```

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is part of the ACMAD e-Safari initiative.

## Support & Issues

- **Repository**: https://github.com/ACMAD-Niamey/data-infrastructure
- **Issue Tracker**: https://github.com/ACMAD-Niamey/data-infrastructure/issues

## Acknowledgments

- Built with [Django](https://www.djangoproject.com/)
- REST API framework by [Django REST Framework](https://www.django-rest-framework.org/)
- Tiles service powered by [TiPG](https://github.com/developmentseed/tipg)
- Geospatial database support via [PostGIS](https://postgis.net/)

---

**Last Updated**: June 2026
