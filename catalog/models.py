from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel

from catalog.widgets import HexColorWidget, LegendMapWidget
from wagtail.fields import RichTextField
from wagtail.images import get_image_model
from wagtail.models import Orderable, Page
from wagtail.snippets.models import register_snippet

Image = get_image_model()


@register_snippet
class HazardCategory(models.Model):
    """Hazard type used to group datasets in the multi-hazard geoportal."""

    key = models.SlugField(unique=True, help_text="Stable slug matching frontend category keys, e.g. drought")
    label = models.CharField(max_length=100)
    icon = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional custom icon; frontend falls back to its built-in lucide icon when not set.",
    )
    order = models.PositiveIntegerField(default=0)

    panels = [
        FieldPanel("key"),
        FieldPanel("label"),
        FieldPanel("icon"),
        FieldPanel("order"),
    ]

    class Meta:
        ordering = ["order"]
        verbose_name = "Hazard category"
        verbose_name_plural = "Hazard categories"

    def __str__(self):
        return self.label


class ProjectPage(Page):
    """A top-level container that groups datasets under one project."""
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    # only allow DatasetPage children
    subpage_types = ["catalog.DatasetPage"]


class DatasetPage(Page):
    """
    A dataset page that lives under a project.
    This is the control-plane record (human-facing + metadata).
    """
    description = RichTextField(blank=True)

    DATASET_TYPES = [
        ("raster", "Raster"),
        ("vector", "Vector"),
    ]

    CADENCES = [
        ("daily", "Daily"),
        ("dekadal", "Dekadal"),
        ("monthly", "Monthly"),
        ("seasonal", "Seasonal"),
    ]

    dataset_id = models.SlugField(
        max_length=80,
        unique=True,
        help_text="Stable id used by infra and APIs, e.g. cdi, spi, sma",
    )
    dataset_type = models.CharField(max_length=10, choices=DATASET_TYPES)
    cadence = models.CharField(max_length=10, choices=CADENCES)

    # links to infra (we will use these later)
    stac_collection_id = models.CharField(
        max_length=120,
        blank=True,
        help_text="If blank, defaults to dataset_id",
    )

    # controls what shows up in the UI config API
    is_published_for_ui = models.BooleanField(default=False)

    hazard_category = models.ForeignKey(
        "catalog.HazardCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="datasets",
        help_text="Hazard type for grouping in the multi-hazard geoportal.",
    )

    icon = models.ForeignKey(
        "catalog.LayerIcon",
        on_delete=models.PROTECT,
        related_name="datasets",
        null=True,
        blank=True,
        help_text="Toolbar icon for this dataset in the UI.",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower values appear first in the UI layer list.",
    )
    color_class = models.CharField(
        max_length=80,
        default="text-blue-600",
        blank=True,
        help_text="Tailwind text color class for icon accent (e.g. text-green-600).",
    )

    content_panels = Page.content_panels + [
        FieldPanel("description"),
        FieldPanel("hazard_category"),
        FieldPanel("icon"),
        FieldPanel("sort_order"),
        FieldPanel("color_class"),
        FieldPanel("dataset_id"),
        FieldPanel("dataset_type"),
        FieldPanel("cadence"),
        FieldPanel("stac_collection_id"),
        FieldPanel("is_published_for_ui"),
    ]

    parent_page_types = ["catalog.ProjectPage"]
    subpage_types = []


STYLE_SCHEME_CHOICES = [
    ("discrete", "Discrete"),
    ("linear", "Linear"),
    ("band", "Band"),
]


@register_snippet
class LayerIcon(models.Model):
    """Reusable toolbar icon for catalog layers (upload SVG/PNG in Wagtail)."""

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    image = models.ForeignKey(
        Image,
        on_delete=models.PROTECT,
        related_name="+",
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
        FieldPanel("image"),
    ]

    class Meta:
        ordering = ["title"]
        verbose_name = "Layer icon"
        verbose_name_plural = "Layer icons"

    def __str__(self):
        return self.title


class LayerColorStop(Orderable):
    layer = ParentalKey(
        "catalog.Layer",
        on_delete=models.CASCADE,
        related_name="color_stops",
    )
    value = models.FloatField()
    color = models.CharField(
        max_length=7,
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$")],
        help_text="#RRGGBB",
    )

    panels = [
        FieldPanel("value"),
        FieldPanel("color", widget=HexColorWidget()),
    ]


@register_snippet
class Layer(ClusterableModel):
    """Optional raster styling config (1:1 with a DatasetPage). Listing uses the dataset."""

    class Meta:
        ordering = ["title"]
        verbose_name = "Layer style"
        verbose_name_plural = "Layer styles"

    LAYER_TYPES = [
        ("raster", "Raster"),
        ("vector", "Vector"),
    ]

    title = models.CharField(max_length=120)
    layer_id = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        help_text="Defaults to dataset_id. Use a distinct id when multiple styles share one dataset.",
    )

    dataset = models.OneToOneField(
        "catalog.DatasetPage",
        on_delete=models.CASCADE,
        related_name="style_config",
    )

    layer_type = models.CharField(max_length=10, choices=LAYER_TYPES)

    description = RichTextField(
        blank=True,
        help_text="Optional layer-specific info text when multiple styles reference the same dataset.",
    )

    tile_template = models.CharField(max_length=300, blank=True, default="")
    tile_params = models.JSONField(default=dict, blank=True)

    style_scheme = models.CharField(
        max_length=20,
        choices=STYLE_SCHEME_CHOICES,
        default="discrete",
        help_text=(
            "Discrete/linear: color stops become a TiTiler colormap. "
            "Band: RGB compositing (default bidx=1,2,3) via band_visualization_params in tile_params."
        ),
    )
    style_min = models.FloatField(
        null=True,
        blank=True,
        help_text="Lower bound for linear ramps (maps to tile_params min).",
    )
    style_max = models.FloatField(
        null=True,
        blank=True,
        help_text="Optional upper hint for discrete/band styling.",
    )
    use_advanced_tile_params = models.BooleanField(
        default=False,
        help_text="When enabled, tile_params JSON is left as-is (no sync from color stops).",
    )
    style_import = models.FileField(
        upload_to="layer_styles/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["qml", "sld"])],
        help_text="Import a QGIS .qml (singleband pseudocolor) or GeoServer .sld (Raster ColorMap).",
    )

    default_visible = models.BooleanField(default=False)
    opacity = models.FloatField(default=0.85)
    minzoom = models.IntegerField(default=0)
    maxzoom = models.IntegerField(default=12)
    legend = models.JSONField(
        default=dict,
        blank=True,
        help_text="Label → color map for the UI legend, e.g. {\"Low\": \"#d73027\", \"High\": \"#1a9850\"}.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("dataset"),
        FieldPanel("title"),
        FieldPanel("layer_id"),
        FieldPanel("description"),
        FieldPanel("layer_type"),
        FieldPanel("tile_template"),
        MultiFieldPanel(
            [
                FieldPanel("style_scheme"),
                FieldPanel("style_min"),
                FieldPanel("style_max"),
                InlinePanel("color_stops", label="Color stops", min_num=0),
                FieldPanel("use_advanced_tile_params"),
                FieldPanel(
                    "tile_params",
                    classname="collapsible",
                ),
                FieldPanel("style_import"),
            ],
            heading="Raster styling",
        ),
        FieldPanel("default_visible"),
        FieldPanel("opacity"),
        FieldPanel("minzoom"),
        FieldPanel("maxzoom"),
        FieldPanel("legend", widget=LegendMapWidget()),
    ]

    def __str__(self):
        if self.dataset_id:
            return f"{self.title} ({self.dataset})"
        return self.title

    def clean(self):
        super().clean()
        if self.legend is None:
            self.legend = {}
        if self.tile_params is None:
            self.tile_params = {}
        if self.dataset_id:
            if not self.layer_id:
                self.layer_id = self.dataset.dataset_id
            elif self.layer_id != self.dataset.dataset_id:
                pass  # allow distinct layer_id for future multi-style datasets
        from catalog.style.normalize import normalize_tile_params
        from catalog.style.parse_qml import parse_qml_raster_pseudocolor
        from catalog.style.parse_sld import parse_sld_raster_colormap

        if self.style_scheme == "band" and not self.use_advanced_tile_params:
            from catalog.style.band_defaults import ensure_band_tile_params

            self.tile_params = ensure_band_tile_params(self.tile_params)

        if self.style_scheme == "band":
            tp = self.tile_params or {}
            if not tp.get("band_visualization_params"):
                raise ValidationError(
                    {
                        "tile_params": "Band scheme requires band_visualization_params inside tile_params "
                        "(raw TiTiler query fragment, e.g. bidx=1&bidx=2&bidx=3 or rescale=0,255&bidx=1)."
                    }
                )

        if self.style_import:
            name = self.style_import.name.lower()
            try:
                self.style_import.seek(0)
                raw_bytes = self.style_import.read()
                text = raw_bytes.decode("utf-8")
                self.style_import.seek(0)
            except OSError as exc:
                raise ValidationError({"style_import": "Could not read uploaded file."}) from exc

            try:
                if name.endswith(".sld"):
                    parsed = parse_sld_raster_colormap(text)
                elif name.endswith(".qml"):
                    parsed = parse_qml_raster_pseudocolor(text)
                else:
                    raise ValidationError({"style_import": "Use a .qml or .sld file."})
                self._pending_style_import = normalize_tile_params(parsed)
            except ValueError as exc:
                raise ValidationError({"style_import": str(exc)}) from exc

    def sync_tile_params_from_stops(self):
        """Rebuild tile_params from inline color stops unless advanced JSON or band scheme."""
        from catalog.style.normalize import normalize_tile_params, split_tile_params

        if getattr(self, "_skip_tile_sync", False):
            return
        if self.pk is None:
            return
        if self.use_advanced_tile_params or self.style_scheme == "band":
            return
        if not self.color_stops.exists():
            return

        _, extras = split_tile_params(self.tile_params or {})
        payload = {**extras}
        payload["scheme"] = self.style_scheme
        payload["values"] = [s.value for s in self.color_stops.order_by("sort_order")]
        payload["palette"] = [s.color for s in self.color_stops.order_by("sort_order")]
        if self.style_min is not None:
            payload["min"] = self.style_min
        if self.style_max is not None:
            payload["max"] = self.style_max
        normalized = normalize_tile_params(payload)
        Layer.objects.filter(pk=self.pk).update(tile_params=normalized)

    def _apply_pending_style_import(self, pending: dict):
        from django.db import transaction

        with transaction.atomic():
            self.color_stops.all().delete()
            for i, (v, c) in enumerate(zip(pending["values"], pending["palette"])):
                LayerColorStop.objects.create(
                    layer=self,
                    sort_order=i,
                    value=float(v),
                    color=c.lower() if c.startswith("#") else f"#{c.lower()}",
                )
            Layer.objects.filter(pk=self.pk).update(
                style_scheme=pending["scheme"],
                style_min=pending.get("min"),
                style_max=pending.get("max"),
                use_advanced_tile_params=False,
                tile_params=pending,
            )
            if self.style_import:
                self.style_import.delete(save=False)

    def save(self, *args, **kwargs):
        if self.dataset_id and not self.layer_id:
            self.layer_id = self.dataset.dataset_id
        pending = getattr(self, "_pending_style_import", None)
        if pending:
            self._skip_tile_sync = True
        if (
            self.style_scheme == "band"
            and not self.use_advanced_tile_params
            and not pending
        ):
            from catalog.style.band_defaults import ensure_band_tile_params

            self.tile_params = ensure_band_tile_params(self.tile_params)
        try:
            super().save(*args, **kwargs)
            if pending:
                self._apply_pending_style_import(pending)
                if hasattr(self, "_pending_style_import"):
                    delattr(self, "_pending_style_import")
        finally:
            self._skip_tile_sync = False
