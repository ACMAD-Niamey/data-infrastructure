# Generated manually for LayerIcon and Layer UI fields

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_alter_layer_legend_alter_layer_style_scheme"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="LayerIcon",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                (
                    "image",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
            ],
            options={
                "verbose_name": "Layer icon",
                "verbose_name_plural": "Layer icons",
                "ordering": ["title"],
            },
        ),
        migrations.AddField(
            model_name="layer",
            name="color_class",
            field=models.CharField(
                blank=True,
                default="text-blue-600",
                help_text="Tailwind text color class for icon accent (e.g. text-green-600).",
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="layer",
            name="icon",
            field=models.ForeignKey(
                blank=True,
                help_text="Icon shown in the e-safari layer toolbar.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="layers",
                to="catalog.layericon",
            ),
        ),
        migrations.AddField(
            model_name="layer",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lower values appear first in the UI layer list.",
            ),
        ),
    ]
