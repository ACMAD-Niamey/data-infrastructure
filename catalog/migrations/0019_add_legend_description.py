from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0018_alter_datasetpage_cadence_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="layer",
            name="legend_description",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="geoserverlayer",
            name="legend_description",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="staticwmslayer",
            name="legend_description",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
    ]
