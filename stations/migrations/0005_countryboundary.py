from django.contrib.gis.db.models import fields
from django.contrib.postgres.indexes import GistIndex
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0004_station_country_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="CountryBoundary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country_name", models.CharField(db_index=True, max_length=150, unique=True)),
                ("country_code", models.CharField(blank=True, db_index=True, max_length=3, null=True)),
                ("geom", fields.MultiPolygonField(srid=4326)),
                ("source_feature_id", models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "country_boundaries",
                "indexes": [
                    GistIndex(fields=["geom"], name="country_boundaries_geom_gix"),
                    models.Index(fields=["country_name"], name="country_boundaries_name_idx"),
                    models.Index(fields=["country_code"], name="country_boundaries_code_idx"),
                ],
            },
        ),
    ]
