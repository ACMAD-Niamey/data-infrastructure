"""Station.metadata_json plus the heat-campaign sensor variable codes."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0010_station_has_observations"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="metadata_json",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text=(
                    "Free-form, source-specific attributes (e.g. campaign, dataset_code, "
                    "exposure, commune). Kept off the typed columns so new station "
                    "sources need no schema change."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="stationsensor",
            name="variable_code",
            field=models.CharField(
                db_index=True,
                max_length=50,
                choices=[
                    ("temp", "Air Temperature"),
                    ("rainfall", "Rainfall"),
                    ("rh", "Relative Humidity"),
                    ("pressure", "Pressure"),
                    ("wind_speed", "Wind Speed"),
                    ("wind_direction", "Wind Direction"),
                    ("solar_radiation", "Solar Radiation"),
                    ("soil_moisture", "Soil Moisture"),
                    ("soil_temp", "Soil Temperature"),
                    ("globe_temp", "Black Globe Temperature"),
                    ("lux", "Illuminance"),
                    ("battery_v", "Battery Voltage"),
                    ("water_level", "Water Level"),
                    ("other", "Other"),
                ],
            ),
        ),
    ]
