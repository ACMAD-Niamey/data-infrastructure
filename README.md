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

## Project Structure

```
geomgr/
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

- **Catalog**: Layer management and metadata
- **Ingest**: Data ingestion jobs and tracking
- **Uploads**: File upload handling
- **VectorIngest**: Vector-specific processing

Migrations are located in each app's `migrations/` directory.

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

**Last Updated**: February 2026
