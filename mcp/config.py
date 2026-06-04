import os

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://web:8070")
STAC_API_URL   = os.getenv("STAC_API_URL",   "http://stac_api:8080")
TITILER_URL    = os.getenv("TITILER_URL",    "http://titiler:80")
TIPG_URL       = os.getenv("TIPG_URL",       "http://tipg:8080")
REDIS_URL      = os.getenv("REDIS_URL",      "redis://redis:6379/1")
