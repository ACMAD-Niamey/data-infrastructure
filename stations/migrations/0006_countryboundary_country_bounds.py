from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0005_countryboundary"),
    ]

    operations = [
        migrations.AddField(
            model_name="countryboundary",
            name="country_bounds",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
