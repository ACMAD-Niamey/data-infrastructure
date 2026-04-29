from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0008_station_stations_canonical_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="countryboundary",
            name="country_code",
            field=models.CharField(blank=True, db_index=True, max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name="station",
            name="canonical_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Canonical country code derived from country boundary dataset.",
                max_length=8,
                null=True,
            ),
        ),
    ]
