from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel

from catalog.widgets import HexColorWidget, LegendMapWidget
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.snippets.models import register_snippet


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

    content_panels = Page.content_panels + [
        FieldPanel("description"),
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
    LAYER_TYPES = [
        ("raster", "Raster"),
        ("vector", "Vector"),
    ]

    title = models.CharField(max_length=120)
    layer_id = models.SlugField(max_length=120, unique=True)

    dataset = models.ForeignKey(
        "catalog.DatasetPage",
        on_delete=models.CASCADE,
        related_name="layer_configs",
    )

    layer_type = models.CharField(max_length=10, choices=LAYER_TYPES)

    tile_template = models.CharField(max_length=300)
    tile_params = models.JSONField(default=dict, blank=True)

    style_scheme = models.CharField(
        max_length=20,
        choices=STYLE_SCHEME_CHOICES,
        default="discrete",
        help_text="How color stops map to the raster (TiTiler colormap).",
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
        FieldPanel("title"),
        FieldPanel("layer_id"),
        FieldPanel("dataset"),
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
        return self.title

    def clean(self):
        super().clean()
        from catalog.style.normalize import normalize_tile_params
        from catalog.style.parse_qml import parse_qml_raster_pseudocolor
        from catalog.style.parse_sld import parse_sld_raster_colormap

        if self.style_scheme == "band":
            tp = self.tile_params or {}
            if not tp.get("band_visualization_params"):
                raise ValidationError(
                    {
                        "tile_params": "Band scheme requires band_visualization_params inside tile_params "
                        "(raw TiTiler query fragment, e.g. rescale=0,100&bidx=1)."
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
        pending = getattr(self, "_pending_style_import", None)
        if pending:
            self._skip_tile_sync = True
        try:
            super().save(*args, **kwargs)
            if pending:
                self._apply_pending_style_import(pending)
                if hasattr(self, "_pending_style_import"):
                    delattr(self, "_pending_style_import")
        finally:
            self._skip_tile_sync = False
