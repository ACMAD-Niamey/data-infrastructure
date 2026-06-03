from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0009_layer_onetoone_style"),
        ("wagtailimages", "0026_delete_uploadedimage"),
    ]

    operations = [
        migrations.CreateModel(
            name="HazardCategory",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(unique=True, help_text="Stable slug matching frontend category keys, e.g. drought")),
                ("label", models.CharField(max_length=100)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "icon",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                        help_text="Optional custom icon; frontend falls back to its built-in lucide icon when not set.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Hazard category",
                "verbose_name_plural": "Hazard categories",
                "ordering": ["order"],
            },
        ),
        migrations.AddField(
            model_name="datasetpage",
            name="hazard_category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="datasets",
                to="catalog.hazardcategory",
                help_text="Hazard type for grouping in the multi-hazard geoportal.",
            ),
        ),
    ]
