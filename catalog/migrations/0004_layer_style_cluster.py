import django.core.validators
import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_alter_layer_options_alter_layer_legend_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="LayerColorStop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                ("value", models.FloatField()),
                (
                    "color",
                    models.CharField(
                        help_text="#RRGGBB",
                        max_length=7,
                        validators=[django.core.validators.RegexValidator("^#[0-9a-fA-F]{6}$")],
                    ),
                ),
                (
                    "layer",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="color_stops",
                        to="catalog.layer",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
        ),
        migrations.AddField(
            model_name="layer",
            name="style_scheme",
            field=models.CharField(
                choices=[
                    ("discrete", "Discrete"),
                    ("linear", "Linear"),
                    ("band", "Band"),
                ],
                default="discrete",
                help_text="How color stops map to the raster (TiTiler colormap).",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="layer",
            name="style_min",
            field=models.FloatField(
                blank=True,
                help_text="Lower bound for linear ramps (maps to tile_params min).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="layer",
            name="style_max",
            field=models.FloatField(
                blank=True,
                help_text="Optional upper hint for discrete/band styling.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="layer",
            name="use_advanced_tile_params",
            field=models.BooleanField(
                default=False,
                help_text="When enabled, tile_params JSON is left as-is (no sync from color stops).",
            ),
        ),
        migrations.AddField(
            model_name="layer",
            name="style_import",
            field=models.FileField(
                blank=True,
                help_text="Import a QGIS .qml (singleband pseudocolor) or GeoServer .sld (Raster ColorMap).",
                null=True,
                upload_to="layer_styles/",
                validators=[django.core.validators.FileExtensionValidator(["qml", "sld"])],
            ),
        ),
    ]
