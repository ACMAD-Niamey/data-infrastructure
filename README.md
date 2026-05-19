# GeoDataManager

A comprehensive Django-based geospatial data management system for handling vector and raster geospatial data with PostGIS, integrated with Celery for asynchronous task processing, and MinIO for cloud-native object storage.

## Project Overview

GeoDataManager is built on the Django framework and provides a RESTful API for managing geospatial datasets. It includes:

- **Catalog Management**: Organize and manage geospatial layers and datasets
- **Vector Data Ingestion**: Import and process vector geospatial data
- **Tile Generation**: OGC-compliant tile services via TiPG
- **Async Processing**: Background job handling with Celery and Redis
- **Cloud Storage**: MinIO integration for scalable object storage
- **API Documentation**: OpenAPI/Swagger documentation with drf-spectacular
- **Authentication & Permissions**: Role-based access control

## Tech Stack

- **Backend**: Django 5.2+ with Django REST Framework
- **CMS**: Wagtail 7.2+ (optional content management)
- **Database**: PostgreSQL with PostGIS extension
- **Task Queue**: Celery with Redis broker
- **Object Storage**: MinIO
- **Tile Service**: TiPG (Tile serving over PostGIS)
- **Web Server**: Gunicorn + Nginx
- **Containerization**: Docker & Docker Compose

## Documentation

- **[Architecture and roadmap](docs/README.md)** — current system diagram (Docker, Django, TiPG, frontends) and future multi-hazard / MCP / LLM plans.

## Project Structure

```
geomgr/
├── docs/                    # Architecture & roadmap (see docs/README.md)
├── catalog/                 # Catalog app for layer management
├── ingest/                  # Vector data ingestion app
├── uploads/                 # File uploads handling
├── vector_ingest/           # Vector data processing
├── home/                    # Homepage/landing page app
├── search/                  # Search functionality
├── geodatamanager/          # Django project settings
│   ├── settings/
│   │   ├── base.py         # Base configuration
│   │   ├── dev.py          # Development settings
│   │   └── production.py    # Production settings
│   ├── celery.py           # Celery configuration
│   ├── urls.py             # Main URL routing
│   └── wsgi.py             # WSGI application
├── docker/                  # Docker entrypoints
├── nginx/                   # Nginx configuration
├── data/                    # Local data storage
├── media/                   # User uploads
├── static/                  # Static files
├── manage.py               # Django management script
├── Makefile                # Development commands
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Multi-service orchestration
└── Dockerfile              # Container image definition
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

### Development Environment

| Service | Port | Purpose |
|---------|------|---------|
| web | 8000 | Django application (Gunicorn) |
| nginx | 80 | Reverse proxy & static file serving |
| db | 5432 | PostgreSQL database (internal) |
| redis | 6379 | Celery message broker (internal) |
| tipg | 8082 | OGC tile service |
| minio | 9000 | Object storage (internal) |
| worker | - | Celery background worker (internal) |

### Production Environment

In production, **only ports 80 and 443** are exposed through Nginx. All internal services communicate via internal Docker network:

| Service | Internal Port | Public Access | Purpose |
|---------|---------------|----------------|---------|
| web | 8000 | https://yourdomain.com | Django application (via Nginx proxy) |
| nginx | 80, 443 | Yes | Reverse proxy & static file serving |
| db | 5432 | No | PostgreSQL database |
| redis | 6379 | No | Celery message broker |
| tipg | 8080 | https://yourdomain.com/tiles | OGC tile service (via Nginx proxy) |
| minio | 9000 | No | Object storage (internal) |
| worker | - | No | Celery background worker |

**Note**: API endpoints are accessed through Nginx reverse proxy:
- Django API: `https://yourdomain.com/api/`
- TiPG Tiles: `https://yourdomain.com/tiles/`
- Admin: `https://yourdomain.com/admin/`

## Environment Variables

Key environment variables (see `.env` or `.env.example`):

```bash
# Django
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_USER=geodatamanager
POSTGRES_PASSWORD=your-password
POSTGRES_DB=geodatamanager
POSTGRES_HOST=db
POSTGRES_PORT=5432

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_URL=http://minio:9000

# Redis
REDIS_URL=redis://redis:6379/0

# Storage
STATIC_VOLUME=/home/app/web/static
MEDIA_VOLUME=/app/media

# TiPG
TIPG_DEBUG=false
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
- [ ] Enable HTTPS/SSL
- [ ] Set up proper logging
- [ ] Configure backup strategy
- [ ] Run migrations on fresh database
- [ ] Collect static files
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

**Last Updated**: April 2026
