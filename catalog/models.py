from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
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




@register_snippet
class Layer(models.Model):
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
    default_visible = models.BooleanField(default=False)
    opacity = models.FloatField(default=0.85)
    minzoom = models.IntegerField(default=0)
    maxzoom = models.IntegerField(default=12)
    legend = models.JSONField(default=dict, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("layer_id"),
        FieldPanel("dataset"),
        FieldPanel("layer_type"),
        FieldPanel("tile_template"),
        FieldPanel("tile_params"),
        FieldPanel("default_visible"),
        FieldPanel("opacity"),
        FieldPanel("minzoom"),
        FieldPanel("maxzoom"),
        FieldPanel("legend"),
    ]

    def __str__(self):
        return self.title
