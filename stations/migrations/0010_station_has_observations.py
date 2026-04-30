from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0009_widen_country_codes"),
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
            sql="""
            UPDATE stations s
            SET has_observations = EXISTS (
                SELECT 1
                FROM observations o
                WHERE o.station_id = s.id
            );
            """,
            reverse_sql="""
            UPDATE stations
            SET has_observations = FALSE;
            """,
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION stations_mark_has_observations()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            AS $$
            BEGIN
                UPDATE stations
                SET has_observations = TRUE
                WHERE id = NEW.station_id
                  AND has_observations = FALSE;
                RETURN NEW;
            END;
            $$;

            DROP TRIGGER IF EXISTS trg_observations_mark_station_has_observations ON observations;
            CREATE TRIGGER trg_observations_mark_station_has_observations
            AFTER INSERT ON observations
            FOR EACH ROW
            EXECUTE FUNCTION stations_mark_has_observations();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trg_observations_mark_station_has_observations ON observations;
            DROP FUNCTION IF EXISTS stations_mark_has_observations();
            """,
        ),
    ]
