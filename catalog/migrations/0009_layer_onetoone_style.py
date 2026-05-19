# Dataset-driven 1:1 layers: style snippet OneToOne, copy listing fields to dataset

import django.db.models.deletion
from django.db import migrations, models
import wagtail.fields


def copy_layer_listing_to_dataset(apps, schema_editor):
    Layer = apps.get_model("catalog", "Layer")
    DatasetPage = apps.get_model("catalog", "DatasetPage")

    for layer in Layer.objects.select_related("dataset").iterator():
        dataset = layer.dataset
        if dataset is None:
            continue
        updated = False
        if getattr(layer, "icon_id", None) and not dataset.icon_id:
            dataset.icon_id = layer.icon_id
            updated = True
        layer_sort = getattr(layer, "sort_order", 0) or 0
        if layer_sort and (dataset.sort_order or 0) == 0:
            dataset.sort_order = layer_sort
            updated = True
        layer_color = getattr(layer, "color_class", "") or ""
        if layer_color and layer_color != "text-blue-600" and (
            not dataset.color_class or dataset.color_class == "text-blue-600"
        ):
            dataset.color_class = layer_color
            updated = True
        if updated:
            dataset.save(update_fields=["icon_id", "sort_order", "color_class"])


def dedupe_layers_per_dataset(apps, schema_editor):
    """Keep one Layer per dataset before OneToOne constraint."""
    Layer = apps.get_model("catalog", "Layer")
    seen = set()
    for layer in Layer.objects.order_by("id").iterator():
        if layer.dataset_id in seen:
            layer.delete()
        else:
            seen.add(layer.dataset_id)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_dataset_ui_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="layer",
            name="description",
            field=wagtail.fields.RichTextField(
                blank=True,
                help_text="Optional layer-specific info text when multiple styles reference the same dataset.",
            ),
        ),
        migrations.AlterField(
            model_name="layer",
            name="layer_id",
            field=models.SlugField(
                blank=True,
                help_text="Defaults to dataset_id. Use a distinct id when multiple styles share one dataset.",
                max_length=120,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="layer",
            name="tile_template",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
        migrations.RunPython(copy_layer_listing_to_dataset, migrations.RunPython.noop),
        migrations.RunPython(dedupe_layers_per_dataset, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="layer",
            name="dataset",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="style_config",
                to="catalog.datasetpage",
            ),
        ),
        migrations.RemoveField(
            model_name="layer",
            name="color_class",
        ),
        migrations.RemoveField(
            model_name="layer",
            name="icon",
        ),
        migrations.RemoveField(
            model_name="layer",
            name="sort_order",
        ),
        migrations.AlterModelOptions(
            name="layer",
            options={
                "ordering": ["title"],
                "verbose_name": "Layer style",
                "verbose_name_plural": "Layer styles",
            },
        ),
    ]
