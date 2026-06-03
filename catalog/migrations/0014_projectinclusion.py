from django.db import migrations, models
import django.db.models.deletion
import wagtail.models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0013_seed_climate_category"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectInclusion",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inclusions",
                        to="catalog.projectpage",
                    ),
                ),
                (
                    "source_project",
                    models.ForeignKey(
                        help_text="Datasets from this project become available in the parent project.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="included_by",
                        to="catalog.projectpage",
                    ),
                ),
                (
                    "default_category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        help_text="Assigned to included datasets that have no category of their own.",
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="catalog.hazardcategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Included project",
                "verbose_name_plural": "Included projects",
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
    ]
