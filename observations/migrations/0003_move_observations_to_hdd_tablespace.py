from django.db import migrations

#: Fixed container-internal path -- the *host* side of this mount is
#: configurable via PG_HDD_TABLESPACE_VOLUME (docker-compose.yml), same
#: pattern as PGDATA_VOLUME / WIS2_DOWNLOAD_DIR elsewhere in this repo.
TABLESPACE_LOCATION = "/mnt/blockstorage/pg_hdd_ts"
TABLESPACE_NAME = "hdd_ts"


def move_observations_to_hdd_tablespace(apps, schema_editor):
    """Relocate `observations` onto a separate (slower/cheaper) disk.

    `observations` is defined as a would-be TimescaleDB hypertable
    (0002_create_observations_hypertable), but on environments where that
    extension isn't installed it silently stays a plain table -- and on the
    box this was written for, it had accumulated ~63GB of dead space from a
    historical bulk load/rollback (689 live rows, 0 live dead tuples, but
    vacuum_count=0 -- never once vacuumed) that plain VACUUM can't reclaim,
    since the free space isn't contiguous at the end of the file. A
    same-disk VACUUM FULL wasn't safe given the root disk's headroom at the
    time (needs ~as much free space again as the table itself).

    Moving a table to a new tablespace rewrites it -- only live rows get
    copied, so this both relocates AND compacts it in one step, and the
    temp space it needs comes from the *target* tablespace's disk, not the
    source. observations is effectively idle (no hot queries, never
    vacuumed), so HDD latency there costs nothing noticeable; the actively
    written raw_payload_logs stays on the primary (fast) disk.

    Silently skips if TABLESPACE_LOCATION isn't mounted/writable -- local
    dev and CI don't bind-mount /mnt/blockstorage into the db service (see
    docker-compose.yml's PG_HDD_TABLESPACE_VOLUME), so there's nothing to
    relocate there. Idempotent: safe to re-run (e.g. via a future
    `migrate --fake` reset) since it checks current state before acting.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_tablespace WHERE spcname = %s", [TABLESPACE_NAME])
        if not cursor.fetchone():
            try:
                cursor.execute(
                    f"CREATE TABLESPACE {TABLESPACE_NAME} LOCATION %s", [TABLESPACE_LOCATION]
                )
            except Exception:
                # Path not mounted, or not writable by the postgres OS user
                # in this environment (local dev / CI) -- nothing to do.
                return

        cursor.execute(
            "SELECT tablespace FROM pg_tables WHERE tablename = 'observations'"
        )
        row = cursor.fetchone()
        if row and row[0] != TABLESPACE_NAME:
            # Blocks concurrent access to observations while it copies --
            # acceptable here since the table is effectively idle. For a
            # busy table this would need an announced maintenance window.
            cursor.execute(f"ALTER TABLE observations SET TABLESPACE {TABLESPACE_NAME}")


def move_observations_back_to_default(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablespace FROM pg_tables WHERE tablename = 'observations'"
        )
        row = cursor.fetchone()
        if row and row[0] == TABLESPACE_NAME:
            cursor.execute("ALTER TABLE observations SET TABLESPACE pg_default")


class Migration(migrations.Migration):
    # CREATE TABLESPACE cannot run inside a transaction block.
    atomic = False

    dependencies = [
        ("observations", "0002_create_observations_hypertable"),
    ]

    operations = [
        migrations.RunPython(
            move_observations_to_hdd_tablespace, move_observations_back_to_default
        ),
    ]
