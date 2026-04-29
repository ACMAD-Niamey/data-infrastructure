from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0006_countryboundary_country_bounds"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="canonical_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Canonical country code derived from country boundary dataset.",
                max_length=3,
                null=True,
            ),
        ),
    ]

