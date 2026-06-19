from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0009_widen_country_codes"),
        ("observations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="has_observations",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="True when at least one observation exists for this station.",
            ),
        ),
        migrations.RunSQL(
            # observations is unmanaged (managed=False) so it only exists in production.
            # Skip the backfill safely when the table is absent (e.g. test DB).
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'observations'
                ) THEN
                    UPDATE stations s
                    SET has_observations = EXISTS (
                        SELECT 1
                        FROM observations o
                        WHERE o.station_id = s.id
                    );
                END IF;
            END
            $$;
            """,
            reverse_sql="""
            UPDATE stations SET has_observations = FALSE;
            """,
        ),
        migrations.RunSQL(
            # Skip trigger creation when observations table is absent.
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'observations'
                ) THEN
                    CREATE OR REPLACE FUNCTION stations_mark_has_observations()
                    RETURNS TRIGGER
                    LANGUAGE plpgsql
                    AS $fn$
                    BEGIN
                        UPDATE stations
                        SET has_observations = TRUE
                        WHERE id = NEW.station_id
                          AND has_observations = FALSE;
                        RETURN NEW;
                    END;
                    $fn$;

                    DROP TRIGGER IF EXISTS trg_observations_mark_station_has_observations ON observations;
                    CREATE TRIGGER trg_observations_mark_station_has_observations
                    AFTER INSERT ON observations
                    FOR EACH ROW
                    EXECUTE FUNCTION stations_mark_has_observations();
                END IF;
            END
            $$;
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trg_observations_mark_station_has_observations ON observations;
            DROP FUNCTION IF EXISTS stations_mark_has_observations();
            """,
        ),
    ]
