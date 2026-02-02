#!/bin/bash
set -o errexit
set -o nounset

echo "Entrypoint: preparing environment..."

# Optional: if you have Redis later
if [ -n "${REDIS_URL:-}" ]; then
  export CELERY_BROKER_URL="${REDIS_URL}"
fi

# Support your naming OR standard naming (pick what you want in .env)
POSTGRES_USER="${POSTGRES_USER:-${POSTGRES_USER:-postgres}}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-${POSTGRES_PASS:-}}"
POSTGRES_DB="${POSTGRES_DB:-${POSTGRES_DBNAME:-}}"
POSTGRES_HOST="${POSTGRES_HOST:-${PG_HOST:-db}}"
POSTGRES_PORT="${POSTGRES_PORT:-${PG_PORT:-5432}}"

# If you want DATABASE_URL style:
if [ -n "${POSTGRES_PASSWORD}" ] && [ -n "${POSTGRES_DB}" ]; then
  export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

python3 << END
import sys, time
import psycopg2

suggest_unrecoverable_after = 30
start = time.time()

while True:
    try:
        psycopg2.connect(
            dbname="${POSTGRES_DB}",
            user="${POSTGRES_USER}",
            password="${POSTGRES_PASSWORD}",
            host="${POSTGRES_HOST}",
            port="${POSTGRES_PORT}",
        )
        break
    except psycopg2.OperationalError as error:
        sys.stderr.write("Waiting for PostgreSQL to become available...\\n")
        if time.time() - start > suggest_unrecoverable_after:
            sys.stderr.write(
                "Taking longer than expected; possible issue: %r\\n" % (error,)
            )
        time.sleep(1)
END

echo "PostgreSQL is available."
exec "$@"
