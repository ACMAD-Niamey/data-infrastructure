from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0014_projectinclusion"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeoServerLayer",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dataset_id", models.SlugField(unique=True, help_text="Unique ID used by the catalog API, e.g. ada-cdi")),
                ("title", models.CharField(max_length=200)),
                ("is_published_for_ui", models.BooleanField(default=False)),
                ("availability_api_url", models.URLField(help_text="Base URL of the availability endpoint")),
                ("data_name", models.CharField(max_length=100, help_text="Value of the data_name query param, e.g. cdi")),
                ("cadence", models.CharField(max_length=10, choices=[("daily","Daily"),("dekadal","Dekadal"),("monthly","Monthly"),("seasonal","Seasonal")])),
                ("wms_url_template", models.TextField(help_text="Full WMS URL template with {year}, {MM}, {DD}, {bbox-epsg-3857} placeholders")),
                ("timescale", models.CharField(max_length=20, blank=True, help_text="Replaces {TS} in the URL template")),
                ("default_visible", models.BooleanField(default=False)),
                ("opacity", models.FloatField(default=0.85)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("color_class", models.CharField(max_length=80, default="text-blue-600", blank=True)),
                ("legend", models.JSONField(default=dict, blank=True)),
                ("description", models.TextField(blank=True)),
                ("coverage", models.CharField(max_length=200, blank=True, default="Africa")),
                ("resolution", models.CharField(max_length=100, blank=True)),
                ("update_frequency", models.CharField(max_length=100, blank=True)),
                ("source_organization", models.CharField(max_length=200, blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("methodology_url", models.URLField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="geoserver_layers",
                        to="catalog.projectpage",
                    ),
                ),
                (
                    "hazard_category",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="catalog.hazardcategory",
                    ),
                ),
                (
                    "icon",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="catalog.layericon",
                    ),
                ),
            ],
            options={
                "verbose_name": "GeoServer layer",
                "verbose_name_plural": "GeoServer layers",
                "ordering": ["sort_order", "title"],
            },
        ),
    ]
