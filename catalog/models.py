from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from stations.models import CountryBoundary

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
    external_system_name = models.CharField(
        max_length=200, blank=True,
        help_text="Name of the linked external system, e.g. Africa Drought System",
    )
    external_system_url = models.URLField(
        blank=True,
        help_text="URL for the 'Go to [System]' button in the layer details panel.",
    )

    panels = [
        FieldPanel("key"),
        FieldPanel("label"),
        FieldPanel("icon"),
        FieldPanel("order"),
        FieldPanel("external_system_name"),
        FieldPanel("external_system_url"),
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
    headline = models.CharField(
        max_length=300,
        blank=True,
        help_text="Hero heading shown on the project homepage.",
    )
    subtitle = models.TextField(
        blank=True,
        help_text="Short paragraph below the headline on the homepage.",
    )
    cities_count = models.CharField(
        max_length=20,
        blank=True,
        help_text="Cities stat on the homepage, e.g. '15+'.",
    )
    hero_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Background image shown on the project homepage.",
    )
    about_title = models.CharField(
        max_length=300,
        blank=True,
        help_text="Heading for the About section, e.g. 'About e-SAFARI'.",
    )
    about_intro = models.CharField(
        max_length=500,
        blank=True,
        help_text="Green tagline below the title, e.g. 'Climate evidence for cooler, greener cities'.",
    )
    about_description = models.TextField(
        blank=True,
        help_text="Body paragraph describing the project on the About page.",
    )
    about_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Image shown on the right side of the About hero section.",
    )
    data_platforms_title = models.CharField(
        max_length=300,
        blank=True,
        help_text="Heading for the Data Platforms overview section, e.g. 'The ACMAD Multi-Hazard Data Infrastructure'.",
    )
    data_platforms_description = models.TextField(
        blank=True,
        help_text="Body paragraph describing the data infrastructure, shown on the Data Platforms page.",
    )
    data_platforms_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Image shown on the right side of the Data Platforms hero section.",
    )
    partners_title = models.CharField(
        max_length=300,
        blank=True,
        help_text="Heading for the Partners page, e.g. 'Partners'.",
    )
    partners_intro = models.CharField(
        max_length=500,
        blank=True,
        help_text="Green tagline, e.g. 'Built through climate, data and planning collaboration'.",
    )
    partners_description = models.TextField(
        blank=True,
        help_text="Body paragraph for the Partners hero section.",
    )
    partners_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Image shown on the right side of the Partners hero.",
    )
    partners_cta_label = models.CharField(
        max_length=200,
        blank=True,
        help_text="CTA button label, e.g. 'Contact ACMAD'.",
    )
    partners_cta_url = models.URLField(
        blank=True,
        help_text="External URL for the CTA button (mailto: or https://).",
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Email address that receives contact form submissions from the Partners page.",
    )
    feedback_title = models.CharField(
        max_length=300,
        blank=True,
        help_text="Feedback page title, e.g. 'Feedback'.",
    )
    feedback_intro = models.CharField(
        max_length=500,
        blank=True,
        help_text="Bold subtitle, e.g. 'Help improve e-SAFARI'.",
    )
    feedback_description = models.TextField(
        blank=True,
        help_text="Short description shown below the subtitle.",
    )
    feedback_email = models.EmailField(
        blank=True,
        help_text="Email address that receives feedback form submissions.",
    )
    recaptcha_site_key = models.CharField(
        max_length=200,
        blank=True,
        help_text="Google reCAPTCHA v2 site key (public). Leave blank to disable CAPTCHA on the feedback form.",
    )
    recaptcha_secret_key = models.CharField(
        max_length=200,
        blank=True,
        help_text="Google reCAPTCHA v2 secret key (private, never exposed in API). Used server-side to verify tokens.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        MultiFieldPanel([
            FieldPanel("headline"),
            FieldPanel("subtitle"),
            FieldPanel("cities_count"),
            FieldPanel("hero_image"),
        ], heading="Homepage"),
        MultiFieldPanel([
            FieldPanel("about_title"),
            FieldPanel("about_intro"),
            FieldPanel("about_description"),
            FieldPanel("about_image"),
        ], heading="About page"),
        MultiFieldPanel([
            FieldPanel("data_platforms_title"),
            FieldPanel("data_platforms_description"),
            FieldPanel("data_platforms_image"),
        ], heading="Data Platforms page"),
        InlinePanel("features", label="Features (What e-SAFARI provides)"),
        MultiFieldPanel([
            FieldPanel("partners_title"),
            FieldPanel("partners_intro"),
            FieldPanel("partners_description"),
            FieldPanel("partners_image"),
            FieldPanel("partners_cta_label"),
            FieldPanel("partners_cta_url"),
            FieldPanel("contact_email"),
        ], heading="Partners page"),
        InlinePanel("partners", label="Partner network"),
        InlinePanel("contact_fields", label="Contact form fields"),
        MultiFieldPanel([
            FieldPanel("feedback_title"),
            FieldPanel("feedback_intro"),
            FieldPanel("feedback_description"),
            FieldPanel("feedback_email"),
            FieldPanel("recaptcha_site_key"),
            FieldPanel("recaptcha_secret_key"),
        ], heading="Feedback page"),
        InlinePanel("feedback_fields", label="Feedback form fields"),
        InlinePanel("faqs", label="FAQs"),
        InlinePanel("inclusions", label="Included projects"),
        InlinePanel("supported_countries", label="Supported Countries"),
    ]

    # only allow DatasetPage children
    subpage_types = ["catalog.DatasetPage"]


class ProjectCountry(Orderable):
    """Maps a supported country to a project for the country selector UI."""

    project = ParentalKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="supported_countries",
    )
    country = models.ForeignKey(
        CountryBoundary,
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels = [FieldPanel("country")]

    class Meta(Orderable.Meta):
        verbose_name = "Supported country"
        verbose_name_plural = "Supported countries"

    def __str__(self):
        return self.country.country_name


class ProjectInclusion(Orderable):
    """Borrows another project's datasets into this project without duplication."""

    project = ParentalKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="inclusions",
    )
    source_project = models.ForeignKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="included_by",
        help_text="Datasets from this project become available in the parent project.",
    )
    default_category = models.ForeignKey(
        "catalog.HazardCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Assigned to included datasets that have no category of their own.",
    )

    panels = [
        FieldPanel("source_project"),
        FieldPanel("default_category"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Included project"
        verbose_name_plural = "Included projects"

    def __str__(self):
        return f"{self.source_project} → {self.project}"


class ProjectFeature(Orderable):
    """One feature card, shared by the 'What e-SAFARI provides' section on the About
    page and the 'What you can explore' section on the homepage."""

    project = ParentalKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="features",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Lucide icon slug, e.g. 'thermometer', 'leaf', 'building-2', 'users'.",
    )
    linked_layer_id = models.SlugField(
        max_length=80,
        blank=True,
        help_text=(
            "dataset_id of the layer to preselect on the geoportal when this card is "
            "clicked (matches the 'id' field returned by /api/catalog/ui/layers), "
            "e.g. 'heat_stress'. Leave blank to open the geoportal with its default layer."
        ),
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("icon_name"),
        FieldPanel("linked_layer_id"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Feature"
        verbose_name_plural = "Features"

    def __str__(self):
        return self.title


class ProjectPartner(Orderable):
    """One partner card in the 'Partner network' section on the Partners page."""

    project = ParentalKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="partners",
    )
    role = models.CharField(
        max_length=200,
        blank=True,
        help_text="Role label shown in green, e.g. 'Regional coordination'.",
    )
    logo = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Partner logo image.",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True, help_text="Partner website URL.")

    panels = [
        FieldPanel("role"),
        FieldPanel("logo"),
        FieldPanel("name"),
        FieldPanel("description"),
        FieldPanel("website_url"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Partner"
        verbose_name_plural = "Partners"

    def __str__(self):
        return self.name


class ProjectContactField(Orderable):
    """One field definition for the Partners page contact form."""

    FIELD_TYPES = [
        ("text",     "Short text"),
        ("email",    "Email address"),
        ("textarea", "Long text"),
    ]

    project = ParentalKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="contact_fields",
    )
    label       = models.CharField(max_length=200)
    field_type  = models.CharField(max_length=20, choices=FIELD_TYPES, default="text")
    required    = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=200, blank=True)

    panels = [
        FieldPanel("label"),
        FieldPanel("field_type"),
        FieldPanel("required"),
        FieldPanel("placeholder"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Contact form field"
        verbose_name_plural = "Contact form fields"

    def __str__(self) -> str:
        return f"{self.label} ({self.field_type})"


class ContactSubmission(models.Model):
    """Stores a submitted Partners page contact form entry."""

    project      = models.ForeignKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="contact_submissions",
    )
    form_data    = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Contact submission"
        verbose_name_plural = "Contact submissions"

    def __str__(self) -> str:
        return f"Submission for {self.project} at {self.submitted_at:%Y-%m-%d %H:%M}"

    @property
    def data_summary(self) -> str:
        return "  |  ".join(f"{k}: {v}" for k, v in (self.form_data or {}).items())


class ProjectFeedbackField(Orderable):
    """One field definition for the Feedback page form."""

    FIELD_TYPES = [
        ("text",           "Short text"),
        ("email",          "Email address"),
        ("textarea",       "Long text"),
        ("country_select", "Country dropdown (from project countries)"),
        ("topic_select",   "Topic dropdown (define choices below)"),
    ]

    project     = ParentalKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="feedback_fields",
    )
    label       = models.CharField(max_length=200)
    field_type  = models.CharField(max_length=20, choices=FIELD_TYPES, default="text")
    required    = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=200, blank=True)
    choices     = models.TextField(
        blank=True,
        help_text="For 'topic_select' only: one option per line.",
    )

    panels = [
        FieldPanel("label"),
        FieldPanel("field_type"),
        FieldPanel("required"),
        FieldPanel("placeholder"),
        FieldPanel("choices"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Feedback form field"
        verbose_name_plural = "Feedback form fields"

    def __str__(self) -> str:
        return f"{self.label} ({self.field_type})"


class ProjectFAQ(Orderable):
    """One FAQ item shown on the Feedback page."""

    project  = ParentalKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="faqs",
    )
    question = models.CharField(max_length=400)
    answer   = models.TextField()

    panels = [
        FieldPanel("question"),
        FieldPanel("answer"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self) -> str:
        return self.question


class FeedbackSubmission(models.Model):
    """Stores a submitted Feedback page form entry."""

    project      = models.ForeignKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="feedback_submissions",
    )
    form_data    = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Feedback submission"
        verbose_name_plural = "Feedback submissions"

    def __str__(self) -> str:
        return f"Feedback for {self.project} at {self.submitted_at:%Y-%m-%d %H:%M}"

    @property
    def data_summary(self) -> str:
        return "  |  ".join(f"{k}: {v}" for k, v in (self.form_data or {}).items())


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
        ("annual", "Annual"),
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

    # Layer detail fields shown in the full details panel
    coverage = models.CharField(
        max_length=200, blank=True, default="Africa",
        help_text="Geographic coverage, e.g. Africa",
    )
    resolution = models.CharField(
        max_length=100, blank=True,
        help_text="Spatial resolution, e.g. 5 km",
    )
    update_frequency = models.CharField(
        max_length=100, blank=True,
        help_text="How often data is updated, e.g. Every 10 days",
    )
    source_organization = models.CharField(
        max_length=200, blank=True,
        help_text="Data source / producer, e.g. ACMAD / Africa Drought System",
    )
    methodology = RichTextField(
        blank=True,
        help_text="Methodology description shown in the full details panel.",
    )
    methodology_url = models.URLField(
        blank=True,
        help_text="Link to external methodology documentation.",
    )
    legend_description = models.TextField(
        blank=True,
        help_text="Short text shown as 'Legend' in the info panel (separate from the main description).",
    )
    example_notebook = models.ForeignKey(
        "wagtaildocs.Document",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Upload a .ipynb Jupyter notebook demonstrating access to this dataset.",
    )
    example_notebook_description = models.CharField(
        max_length=300, blank=True,
        help_text="Optional one-line caption/description for the example notebook.",
    )
    has_stac_collection = models.BooleanField(
        default=True,
        help_text="Whether this dataset has a real STAC collection registered in pgSTAC. "
                   "Uncheck to hide the 'View STAC collection' link on the Data Platforms page.",
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
        MultiFieldPanel(
            [
                FieldPanel("coverage"),
                FieldPanel("resolution"),
                FieldPanel("update_frequency"),
                FieldPanel("source_organization"),
                FieldPanel("methodology"),
                FieldPanel("methodology_url"),
                FieldPanel("legend_description"),
                FieldPanel("example_notebook"),
                FieldPanel("example_notebook_description"),
                FieldPanel("has_stac_collection"),
            ],
            heading="Layer details",
        ),
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


@register_snippet
class GeoServerLayer(models.Model):
    """
    An externally-hosted WMS layer served via GeoServer.
    Availability is fetched from the external system's API; tile URLs are
    constructed from a template and proxied through the catalog endpoints so
    the frontend needs no changes.
    """

    dataset_id = models.SlugField(
        unique=True,
        help_text="Unique ID used by the catalog API, e.g. ada-cdi",
    )
    title = models.CharField(max_length=200)
    project = models.ForeignKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="geoserver_layers",
    )
    hazard_category = models.ForeignKey(
        "catalog.HazardCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    icon = models.ForeignKey(
        "catalog.LayerIcon",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    is_published_for_ui = models.BooleanField(default=False)

    # External availability API
    availability_api_url = models.URLField(
        help_text="Base URL of the availability endpoint, e.g. https://ada.acmad.org/api/data_api/rs_data/get_available_datasets/",
    )
    data_name = models.CharField(
        max_length=100,
        help_text="Value of the data_name query param, e.g. cdi",
    )
    cadence = models.CharField(max_length=10, choices=DatasetPage.CADENCES)

    # GeoServer WMS tile URL template
    wms_url_template = models.TextField(
        help_text=(
            "Full WMS URL template. Use {year}, {MM}, {DD}, {TS} as date placeholders. "
            "Keep {bbox-epsg-3857} — MapLibre fills it in dynamically. "
            "Copy the url_template value from the external availability API response."
        ),
    )
    timescale = models.CharField(
        max_length=20,
        blank=True,
        help_text="Replaces {TS} in the URL template, e.g. 48 for SPI-48",
    )

    # UI display config
    default_visible = models.BooleanField(default=False)
    opacity = models.FloatField(default=0.85)
    sort_order = models.PositiveIntegerField(default=0)
    color_class = models.CharField(max_length=80, default="text-blue-600", blank=True)
    legend = models.JSONField(
        default=dict,
        blank=True,
        help_text='Label → hex color map, e.g. {"No Warning": "#ffffff"}',
    )
    description = RichTextField(blank=True)

    # Layer detail fields (same set as the Layer snippet)
    coverage = models.CharField(max_length=200, blank=True, default="Africa")
    resolution = models.CharField(max_length=100, blank=True, help_text="e.g. 5 km")
    update_frequency = models.CharField(max_length=100, blank=True, help_text="e.g. Every 10 days")
    source_organization = models.CharField(max_length=200, blank=True)
    methodology = RichTextField(blank=True)
    methodology_url = models.URLField(blank=True)
    legend_description = models.TextField(blank=True)
    has_stac_collection = models.BooleanField(
        default=False,
        help_text="Whether this dataset has a real STAC collection registered in pgSTAC. "
                   "Uncheck to hide the 'View STAC collection' link on the Data Platforms page.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("project"),
        FieldPanel("dataset_id"),
        FieldPanel("title"),
        FieldPanel("hazard_category"),
        FieldPanel("icon"),
        FieldPanel("is_published_for_ui"),
        MultiFieldPanel(
            [
                FieldPanel("availability_api_url"),
                FieldPanel("data_name"),
                FieldPanel("cadence"),
                FieldPanel("wms_url_template"),
                FieldPanel("timescale"),
            ],
            heading="GeoServer config",
        ),
        MultiFieldPanel(
            [
                FieldPanel("default_visible"),
                FieldPanel("opacity"),
                FieldPanel("sort_order"),
                FieldPanel("color_class"),
                FieldPanel("legend", widget=LegendMapWidget()),
            ],
            heading="UI config",
        ),
        FieldPanel("description"),
        MultiFieldPanel(
            [
                FieldPanel("coverage"),
                FieldPanel("resolution"),
                FieldPanel("update_frequency"),
                FieldPanel("source_organization"),
                FieldPanel("methodology"),
                FieldPanel("methodology_url"),
                FieldPanel("legend_description"),
                FieldPanel("has_stac_collection"),
            ],
            heading="Layer details",
        ),
    ]

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "ADMA GeoServer layer"
        verbose_name_plural = "ADMA GeoServer layers"

    def __str__(self):
        return self.title


@register_snippet
class StaticWmsLayer(models.Model):
    """
    A static WMS or XYZ tile layer with a permanent URL and no date dimension.
    Use this for reference layers such as country boundaries or administrative
    divisions that do not change over time.
    """

    dataset_id = models.SlugField(
        unique=True,
        help_text="Unique ID used by the catalog API, e.g. countries-boundary",
    )
    title = models.CharField(max_length=200)
    project = models.ForeignKey(
        "catalog.ProjectPage",
        on_delete=models.CASCADE,
        related_name="static_wms_layers",
    )
    hazard_category = models.ForeignKey(
        "catalog.HazardCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    icon = models.ForeignKey(
        "catalog.LayerIcon",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    is_published_for_ui = models.BooleanField(default=False)

    tile_url = models.TextField(
        help_text=(
            "Full tile URL. Use {bbox-epsg-3857} for WMS GetMap requests, "
            "or {z}/{x}/{y} placeholders for XYZ/TMS tile services."
        ),
    )

    legend = models.JSONField(
        default=dict,
        blank=True,
        help_text='Label → hex color map, e.g. {"Country border": "#333333"}',
    )
    description = RichTextField(blank=True)

    default_visible = models.BooleanField(default=False)
    always_on_top = models.BooleanField(
        default=False,
        help_text=(
            "Keep this layer rendered above every other active layer, e.g. an "
            "admin-boundary overlay that should stay visible over hazard rasters."
        ),
    )
    display_on_homepage = models.BooleanField(
        default=False,
        help_text=(
            "Show this layer on the homepage hero map, alongside whichever hazard "
            "category the visitor has selected. Combine with 'Always on top' to keep "
            "it above the homepage's category raster too."
        ),
    )
    opacity = models.FloatField(default=0.85)
    sort_order = models.PositiveIntegerField(default=0)
    color_class = models.CharField(max_length=80, default="text-blue-600", blank=True)

    coverage = models.CharField(max_length=200, blank=True, default="Africa")
    source_organization = models.CharField(max_length=200, blank=True)
    legend_description = models.TextField(blank=True)
    has_stac_collection = models.BooleanField(
        default=False,
        help_text="Whether this dataset has a real STAC collection registered in pgSTAC. "
                   "Uncheck to hide the 'View STAC collection' link on the Data Platforms page.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("project"),
        FieldPanel("dataset_id"),
        FieldPanel("title"),
        FieldPanel("hazard_category"),
        FieldPanel("icon"),
        FieldPanel("is_published_for_ui"),
        MultiFieldPanel(
            [FieldPanel("tile_url")],
            heading="Tile URL",
        ),
        MultiFieldPanel(
            [
                FieldPanel("default_visible"),
                FieldPanel("always_on_top"),
                FieldPanel("display_on_homepage"),
                FieldPanel("opacity"),
                FieldPanel("sort_order"),
                FieldPanel("color_class"),
                FieldPanel("legend", widget=LegendMapWidget()),
            ],
            heading="UI config",
        ),
        FieldPanel("description"),
        MultiFieldPanel(
            [
                FieldPanel("coverage"),
                FieldPanel("source_organization"),
                FieldPanel("legend_description"),
                FieldPanel("has_stac_collection"),
            ],
            heading="Layer details",
        ),
    ]

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "Static WMS / tile layer"
        verbose_name_plural = "Static WMS / tile layers"

    def __str__(self):
        return self.title
