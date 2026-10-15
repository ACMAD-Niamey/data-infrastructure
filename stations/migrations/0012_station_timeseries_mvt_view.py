"""TiPG view for station time-series datasets (e.g. the Niamey heat campaign)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0011_station_metadata_json_sensor_variables"),
    ]

    operations = [
        # A dedicated view (not stations_mvt) because these points are filtered
        # by dataset_code, which lives in metadata_json. Exposing it as a real
        # column lets TiPG's ?filter= / CQL2 select one dataset's locations.
        migrations.RunSQL(
            sql="""
            CREATE SCHEMA IF NOT EXISTS tiles;

            CREATE OR REPLACE VIEW tiles.station_timeseries_mvt AS
            SELECT
                s.id,
                s.station_code,
                COALESCE(s.name, '') AS name,
                s.metadata_json ->> 'dataset_code' AS dataset_code,
                s.metadata_json ->> 'exposure'     AS exposure,
                s.metadata_json ->> 'site'         AS site,
                s.metadata_json ->> 'commune'      AS commune,
                s.metadata_json ->> 'group'        AS site_group,
                s.country_code,
                s.geom::geometry(Point, 4326) AS geom
            FROM stations s
            WHERE s.is_active = TRUE
              AND s.geom IS NOT NULL
              AND s.metadata_json ? 'dataset_code';
            """,
            reverse_sql="DROP VIEW IF EXISTS tiles.station_timeseries_mvt;",
        ),
    ]
