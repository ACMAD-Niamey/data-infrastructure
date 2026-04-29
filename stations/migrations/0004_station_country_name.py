from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0003_stations_mvt_tile_view"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="country_name",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Human-readable country name derived from ISO mapping or reverse geocoding.",
                max_length=150,
                null=True,
            ),
        ),
    ]

