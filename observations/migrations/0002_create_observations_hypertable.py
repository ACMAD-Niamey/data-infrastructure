from django.db import migrations

# ---------------------------------------------------------------------------
# The observations table DDL (no TimescaleDB-specific calls)
# ---------------------------------------------------------------------------
CREATE_OBSERVATIONS_SQL = """
CREATE TABLE IF NOT EXISTS observations (
    station_id BIGINT NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    sensor_id BIGINT NULL REFERENCES station_sensors(id) ON DELETE SET NULL,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    source_id BIGINT NOT NULL REFERENCES data_sources(id) ON DELETE RESTRICT,

    observed_at TIMESTAMPTZ NOT NULL,
    variable_code VARCHAR(50) NOT NULL,

    raw_value DOUBLE PRECISION NULL,
    cleaned_value DOUBLE PRECISION NULL,
    unit VARCHAR(50) NULL,

    qc_flag VARCHAR(20) NOT NULL DEFAULT 'unchecked',
    qc_notes TEXT NULL,

    ingest_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_ref VARCHAR(255) NULL,

    PRIMARY KEY (station_id, variable_code, observed_at)
);

CREATE INDEX IF NOT EXISTS obs_station_time_idx
    ON observations (station_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_variable_time_idx
    ON observations (variable_code, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_dataset_time_idx
    ON observations (dataset_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_source_time_idx
    ON observations (source_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS obs_qc_flag_idx
    ON observations (qc_flag);
"""


def setup_timescaledb(apps, schema_editor):
    """Convert the observations table to a TimescaleDB hypertable.

    Silently skips if the TimescaleDB extension is not available (e.g. in
    the Django test runner which uses a plain PostgreSQL database).
    Uses a SAVEPOINT so a failed create_hypertable call does not abort
    the surrounding migration transaction.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SAVEPOINT pre_hypertable")
        try:
            cursor.execute(
                "SELECT create_hypertable('observations', 'observed_at', if_not_exists => TRUE);"
            )
            cursor.execute(
                "SELECT set_chunk_time_interval('observations', INTERVAL '7 days');"
            )
            cursor.execute("RELEASE SAVEPOINT pre_hypertable")
        except Exception:
            # TimescaleDB is not installed — roll back just this savepoint
            # so the surrounding transaction remains valid.
            cursor.execute("ROLLBACK TO SAVEPOINT pre_hypertable")


class Migration(migrations.Migration):

    dependencies = [
        ("observations", "0001_initial"),
        ("stations", "0001_initial"),
        ("sources", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_OBSERVATIONS_SQL,
            reverse_sql="DROP TABLE IF EXISTS observations CASCADE;",
        ),
        migrations.RunPython(setup_timescaledb, migrations.RunPython.noop),
    ]
