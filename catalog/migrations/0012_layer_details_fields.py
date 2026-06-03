from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_seed_hazard_categories"),
    ]

    operations = [
        # Layer detail fields
        migrations.AddField(
            model_name="layer",
            name="coverage",
            field=models.CharField(blank=True, default="Africa", max_length=200,
                                   help_text="Geographic coverage, e.g. Africa"),
        ),
        migrations.AddField(
            model_name="layer",
            name="resolution",
            field=models.CharField(blank=True, default="", max_length=100,
                                   help_text="Spatial resolution, e.g. 5 km"),
        ),
        migrations.AddField(
            model_name="layer",
            name="update_frequency",
            field=models.CharField(blank=True, default="", max_length=100,
                                   help_text="How often data is updated, e.g. Every 10 days"),
        ),
        migrations.AddField(
            model_name="layer",
            name="source_organization",
            field=models.CharField(blank=True, default="", max_length=200,
                                   help_text="Data source / producer, e.g. ACMAD / Africa Drought System"),
        ),
        migrations.AddField(
            model_name="layer",
            name="methodology",
            field=models.TextField(blank=True, default="",
                                   help_text="Methodology description shown in the full details panel."),
        ),
        migrations.AddField(
            model_name="layer",
            name="methodology_url",
            field=models.URLField(blank=True, default="",
                                  help_text="Link to external methodology documentation."),
        ),
        # HazardCategory external system fields
        migrations.AddField(
            model_name="hazardcategory",
            name="external_system_name",
            field=models.CharField(blank=True, default="", max_length=200,
                                   help_text="Name of the linked external system, e.g. Africa Drought System"),
        ),
        migrations.AddField(
            model_name="hazardcategory",
            name="external_system_url",
            field=models.URLField(blank=True, default="",
                                  help_text="URL for the 'Go to [System]' button in the layer details panel."),
        ),
    ]
