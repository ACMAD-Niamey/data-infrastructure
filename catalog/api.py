from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from wagtail.rich_text import expand_db_html

from catalog.models import (
    ContactSubmission, FeedbackSubmission,
    GeoServerLayer, StaticWmsLayer,
    HazardCategory, ProjectPage, ProjectCountry,
)
from catalog.serializers import UILayersResponseSerializer
from catalog.ui_layers import dataset_entries_for_project, dataset_to_api_dict, _description_raw_html


def geoserver_layer_to_api_dict(layer: GeoServerLayer, request) -> dict:
    """Serialise a GeoServerLayer to the same shape as dataset_to_api_dict."""
    icon = None
    if layer.icon_id and layer.icon and layer.icon.image_id:
        file_url = layer.icon.image.file.url
        icon = {
            "slug": layer.icon.slug,
            "url": request.build_absolute_uri(file_url) if request else file_url,
        }

    raw_html = _description_raw_html(layer.description)
    if raw_html:
        from django.utils.html import strip_tags
        html = expand_db_html(raw_html)
        description = {"html": html, "plain": strip_tags(html).strip()}
    else:
        description = {"html": "", "plain": ""}

    details = {
        "coverage":            layer.coverage or "Africa",
        "resolution":          layer.resolution or "",
        "update_frequency":    layer.update_frequency or "",
        "source_organization": layer.source_organization or "",
        "methodology_html":    expand_db_html(_description_raw_html(layer.methodology)),
        "methodology_url":     layer.methodology_url or "",
        "legend_description":  layer.legend_description or "",
        "has_notebook":        False,  # GeoServerLayer doesn't support notebooks in v1
    }

    return {
        "id":              layer.dataset_id,
        "title":           layer.title,
        "type":            "raster",
        "project":         layer.project.slug if layer.project_id else None,
        "hazard_category": layer.hazard_category.key if layer.hazard_category_id else None,
        "details":         details,
        "description":     description,
        "icon":            icon,
        "dataset": {
            "id":           layer.dataset_id,
            "title":        layer.title,
            "cadence":      layer.cadence,
            "dataset_type": "raster",
            "stac_collection": "",
        },
        "selection":  {"cadence": layer.cadence},
        "tile":       {"template": layer.wms_url_template, "params": {}},
        "ui": {
            "default_visible":     layer.default_visible,
            "always_on_top":       False,
            "display_on_homepage": False,
            "opacity":             layer.opacity,
            "minzoom":             0,
            "maxzoom":             12,
            "color_class":         layer.color_class or "text-blue-600",
        },
        "legend":     layer.legend or {},
        "updated_at": layer.updated_at.isoformat(),
    }


def static_wms_to_api_dict(layer: StaticWmsLayer, request) -> dict:
    """Serialise a StaticWmsLayer to the same shape as dataset_to_api_dict."""
    icon = None
    if layer.icon_id and layer.icon and layer.icon.image_id:
        file_url = layer.icon.image.file.url
        icon = {
            "slug": layer.icon.slug,
            "url": request.build_absolute_uri(file_url) if request else file_url,
        }

    raw_html = _description_raw_html(layer.description)
    if raw_html:
        from django.utils.html import strip_tags
        html = expand_db_html(raw_html)
        description = {"html": html, "plain": strip_tags(html).strip()}
    else:
        description = {"html": "", "plain": ""}

    details = {
        "coverage":            layer.coverage or "Africa",
        "resolution":          "",
        "update_frequency":    "Static",
        "source_organization": layer.source_organization or "",
        "methodology_html":    "",
        "methodology_url":     "",
        "legend_description":  layer.legend_description or "",
        "has_notebook":        False,  # StaticWmsLayer doesn't support notebooks in v1
    }

    return {
        "id":              layer.dataset_id,
        "title":           layer.title,
        "type":            "raster",
        "project":         layer.project.slug if layer.project_id else None,
        "hazard_category": layer.hazard_category.key if layer.hazard_category_id else None,
        "details":         details,
        "description":     description,
        "icon":            icon,
        "dataset": {
            "id":           layer.dataset_id,
            "title":        layer.title,
            "cadence":      "monthly",
            "dataset_type": "raster",
            "stac_collection": "",
        },
        "selection":  {"cadence": "monthly"},
        "tile":       {"template": layer.tile_url, "params": {}},
        "ui": {
            "default_visible":     layer.default_visible,
            "always_on_top":       layer.always_on_top,
            "display_on_homepage": layer.display_on_homepage,
            "opacity":             layer.opacity,
            "minzoom":             0,
            "maxzoom":             22,
            "color_class":         layer.color_class or "text-blue-600",
        },
        "legend":     layer.legend or {},
        "updated_at": layer.updated_at.isoformat(),
    }


class UILayersView(APIView):
    """
    Read-only config endpoint consumed by React/MapLibre.
    Returns published layers for a Wagtail project (page slug).
    """

    @extend_schema(
        responses={200: UILayersResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="project",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Wagtail project page slug (e.g. e-safari)",
            )
        ],
        tags=["catalog"],
        summary="Get UI layer configurations for a project",
        description=(
            "Returns published datasets under the given project (is_published_for_ui, "
            "with icon). Optional 1:1 Layer style snippet supplies legend and tile params."
        ),
    )
    def get(self, request):
        project_slug = (request.query_params.get("project") or "").strip()
        if not project_slug:
            return Response(
                {"detail": "Query parameter 'project' is required (e.g. ?project=e-safari)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ProjectPage.objects.live().filter(slug=project_slug).exists():
            return Response(
                {"detail": f"Unknown or unpublished project '{project_slug}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            entries = dataset_entries_for_project(project_slug)
        except ProjectPage.DoesNotExist:
            return Response(
                {"detail": f"Unknown or unpublished project '{project_slug}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        out = [dataset_to_api_dict(e.dataset, request, e.category_override) for e in entries]

        # Append externally-hosted GeoServer WMS layers for this project
        gs_qs = (
            GeoServerLayer.objects
            .filter(project__slug=project_slug, is_published_for_ui=True)
            .select_related("icon", "icon__image", "hazard_category", "project")
            .order_by("sort_order", "title")
        )
        out.extend(geoserver_layer_to_api_dict(gs, request) for gs in gs_qs)

        # Append static WMS / XYZ tile layers for this project
        sw_qs = (
            StaticWmsLayer.objects
            .filter(project__slug=project_slug, is_published_for_ui=True)
            .select_related("icon", "icon__image", "hazard_category", "project")
            .order_by("sort_order", "title")
        )
        out.extend(static_wms_to_api_dict(sw, request) for sw in sw_qs)

        return Response({"version": "1.0", "project": project_slug, "layers": out})


class ProjectCountriesView(APIView):
    """Returns supported countries for a project, for use in the country selector UI."""

    @extend_schema(
        tags=["catalog"],
        summary="List supported countries for a project",
        description="Returns countries linked to the project in Wagtail admin, with map bounds for zoom.",
    )
    def get(self, request, slug: str):
        try:
            project = ProjectPage.objects.live().get(slug=slug)
        except ProjectPage.DoesNotExist:
            return Response({"detail": f"Unknown or unpublished project '{slug}'."}, status=status.HTTP_404_NOT_FOUND)

        out = []
        for pc in project.supported_countries.select_related("country").all():
            c = pc.country
            if not c.country_bounds or not c.country_code:
                continue
            out.append({
                "value": c.country_code,
                "label": c.country_name,
                "bounds": c.country_bounds,
            })
        return Response(out)


class ProjectConfigView(APIView):
    """Returns project-level configuration including the hero image URL for the homepage."""

    @extend_schema(
        tags=["catalog"],
        summary="Get project configuration",
        description="Returns project metadata including the hero background image URL.",
    )
    def get(self, request, slug: str):
        try:
            project = ProjectPage.objects.live().get(slug=slug)
        except ProjectPage.DoesNotExist:
            return Response({"detail": f"Unknown or unpublished project '{slug}'."}, status=status.HTTP_404_NOT_FOUND)

        hero_image_url = None
        if project.hero_image_id and project.hero_image:
            hero_image_url = request.build_absolute_uri(project.hero_image.file.url)

        about_image_url = None
        if project.about_image_id and project.about_image:
            about_image_url = request.build_absolute_uri(project.about_image.file.url)

        data_platforms_image_url = None
        if project.data_platforms_image_id and project.data_platforms_image:
            data_platforms_image_url = request.build_absolute_uri(project.data_platforms_image.file.url)

        entries = dataset_entries_for_project(project.slug)
        gs_count = GeoServerLayer.objects.filter(project__slug=project.slug, is_published_for_ui=True).count()
        sw_count = StaticWmsLayer.objects.filter(project__slug=project.slug, is_published_for_ui=True).count()
        layer_count = len(entries) + gs_count + sw_count

        features = [
            {
                "title": f.title,
                "description": f.description,
                "icon_name": f.icon_name,
                "layer_id": f.linked_layer_id or None,
            }
            for f in project.features.all()
        ]

        partners_image_url = None
        if project.partners_image_id and project.partners_image:
            partners_image_url = request.build_absolute_uri(project.partners_image.file.url)

        partners = []
        for p in project.partners.select_related("logo").all():
            logo_url = None
            if p.logo_id and p.logo:
                logo_url = request.build_absolute_uri(p.logo.file.url)
            partners.append({
                "role": p.role,
                "logo_url": logo_url,
                "name": p.name,
                "description": p.description,
                "website_url": p.website_url,
            })

        return Response({
            "slug": project.slug,
            "hero_image_url": hero_image_url,
            "headline": project.headline or project.title,
            "subtitle": project.subtitle,
            "cities_count": project.cities_count,
            "layer_count": layer_count,
            "about_title": project.about_title,
            "about_intro": project.about_intro,
            "about_description": project.about_description,
            "about_image_url": about_image_url,
            "data_platforms_title": project.data_platforms_title,
            "data_platforms_description": project.data_platforms_description,
            "data_platforms_image_url": data_platforms_image_url,
            "features": features,
            "partners_title": project.partners_title,
            "partners_intro": project.partners_intro,
            "partners_description": project.partners_description,
            "partners_image_url": partners_image_url,
            "partners_cta_label": project.partners_cta_label,
            "partners_cta_url": project.partners_cta_url,
            "partners": partners,
            "contact_form_fields": [
                {
                    "label":       f.label,
                    "field_type":  f.field_type,
                    "required":    f.required,
                    "placeholder": f.placeholder,
                }
                for f in project.contact_fields.all()
            ],
            "feedback_title":       project.feedback_title,
            "feedback_intro":       project.feedback_intro,
            "feedback_description": project.feedback_description,
            "recaptcha_site_key":   project.recaptcha_site_key if (project.recaptcha_site_key and project.recaptcha_secret_key) else "",
            "feedback_form_fields": [
                {
                    "label":       f.label,
                    "field_type":  f.field_type,
                    "required":    f.required,
                    "placeholder": f.placeholder,
                    "choices":     [c.strip() for c in f.choices.splitlines() if c.strip()],
                }
                for f in project.feedback_fields.all()
            ],
            "faqs": [
                {"question": faq.question, "answer": faq.answer}
                for faq in project.faqs.all()
            ],
        })


class HazardCategoriesView(APIView):
    """Returns all hazard categories ordered by their display order."""

    @extend_schema(
        tags=["catalog"],
        summary="List hazard categories",
        description="Returns ordered hazard categories used to group datasets in the multi-hazard geoportal.",
    )
    def get(self, request):
        cats = HazardCategory.objects.all()
        return Response([
            {
                "key": c.key,
                "label": c.label,
                "icon_url": request.build_absolute_uri(c.icon.file.url) if c.icon else None,
                "order": c.order,
                "external_system_name": c.external_system_name,
                "external_system_url": c.external_system_url,
            }
            for c in cats
        ])


class ContactSubmitView(APIView):
    """Accepts a contact form POST for a project, stores the submission and emails the project contact."""

    # Public endpoint — no session auth so CSRF is never enforced.
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(tags=["catalog"], summary="Submit contact form")
    def post(self, request, slug: str):
        try:
            project = ProjectPage.objects.live().get(slug=slug)
        except ProjectPage.DoesNotExist:
            return Response({"detail": f"Unknown or unpublished project '{slug}'."}, status=status.HTTP_404_NOT_FOUND)

        fields = list(project.contact_fields.all())
        if not fields:
            return Response({"detail": "No contact form is defined for this project."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data or {}
        errors: dict[str, str] = {}
        clean: dict[str, str] = {}
        for f in fields:
            raw = data.get(f.label, "")
            value = "" if raw is None else str(raw).strip()
            if f.required and not value:
                errors[f.label] = "This field is required."
            elif f.field_type == "email" and value:
                try:
                    validate_email(value)
                except ValidationError:
                    errors[f.label] = "Enter a valid email address."
            clean[f.label] = value

        if errors:
            return Response({"errors": errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        submission = ContactSubmission.objects.create(project=project, form_data=clean)

        if project.contact_email:
            body = "\n".join(f"{k}: {v}" for k, v in clean.items())
            send_mail(
                subject=f"Contact form submission — {project.title}",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[project.contact_email],
                fail_silently=True,
            )

        return Response({"ok": True, "id": submission.pk}, status=status.HTTP_201_CREATED)


class FeedbackSubmitView(APIView):
    """Accepts a feedback form POST, stores the submission and emails the project feedback address."""

    # Public endpoint — no session auth so CSRF is never enforced.
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(tags=["catalog"], summary="Submit feedback form")
    def post(self, request, slug: str):
        try:
            project = ProjectPage.objects.live().get(slug=slug)
        except ProjectPage.DoesNotExist:
            return Response({"detail": f"Unknown or unpublished project '{slug}'."}, status=status.HTTP_404_NOT_FOUND)

        fields = list(project.feedback_fields.all())
        if not fields:
            return Response({"detail": "No feedback form is defined for this project."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify reCAPTCHA token when both keys are configured for this project.
        if project.recaptcha_site_key and project.recaptcha_secret_key:
            import requests as http_req
            token = (request.data or {}).get("recaptcha_token", "")
            try:
                verify = http_req.post(
                    "https://www.google.com/recaptcha/api/siteverify",
                    data={"secret": project.recaptcha_secret_key, "response": token},
                    timeout=5,
                )
                verify.raise_for_status()
                success = bool((verify.json() or {}).get("success"))
            except Exception:
                success = False

            if not success:
                return Response(
                    {"detail": "CAPTCHA verification failed. Please try again."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        data = request.data
        errors: dict = {}
        clean: dict = {}
        for f in fields:
            value = str(data.get(f.label, "")).strip()
            if f.required and not value:
                errors[f.label] = "This field is required."
            clean[f.label] = value

        if errors:
            return Response({"errors": errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        submission = FeedbackSubmission.objects.create(project=project, form_data=clean)

        if project.feedback_email:
            body = "\n".join(f"{k}: {v}" for k, v in clean.items())
            send_mail(
                subject=f"Feedback submission — {project.title}",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[project.feedback_email],
                fail_silently=True,
            )

        return Response({"ok": True, "id": submission.pk}, status=status.HTTP_201_CREATED)
