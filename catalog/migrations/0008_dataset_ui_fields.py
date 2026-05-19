# Generated manually for dataset-driven UI layers

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0007_alter_layer_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="datasetpage",
            name="color_class",
            field=models.CharField(
                blank=True,
                default="text-blue-600",
                help_text="Tailwind text color class for icon accent (e.g. text-green-600).",
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="datasetpage",
            name="icon",
            field=models.ForeignKey(
                blank=True,
                help_text="Toolbar icon for this dataset in the e-safari UI.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="datasets",
                to="catalog.layericon",
            ),
        ),
        migrations.AddField(
            model_name="datasetpage",
            name="sort_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lower values appear first in the UI layer list.",
            ),
        ),
    ]
