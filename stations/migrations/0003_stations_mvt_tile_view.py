"""PostGIS view for TiPG vector tiles (schema tiles)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0002_alter_station_id_alter_stationalias_id_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE SCHEMA IF NOT EXISTS tiles;

            CREATE OR REPLACE VIEW tiles.stations_mvt AS
            SELECT
                s.id,
                s.station_code,
                COALESCE(s.name, '') AS name,
                s.country_code,
                COALESCE(s.admin1, '') AS admin1,
                COALESCE(s.admin2, '') AS admin2,
                s.geom::geometry(Point, 4326) AS geom
            FROM stations s
            WHERE s.is_active = TRUE
              AND s.geom IS NOT NULL;
            """,
            reverse_sql="DROP VIEW IF EXISTS tiles.stations_mvt;",
        ),
    ]
