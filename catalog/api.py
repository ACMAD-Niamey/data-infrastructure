from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from django.utils import timezone
from wagtail.rich_text import expand_db_html

from catalog.models import GeoServerLayer, StaticWmsLayer, HazardCategory, ProjectPage
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
            "default_visible": layer.default_visible,
            "opacity":         layer.opacity,
            "minzoom":         0,
            "maxzoom":         12,
            "color_class":     layer.color_class or "text-blue-600",
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
            "default_visible": layer.default_visible,
            "opacity":         layer.opacity,
            "minzoom":         0,
            "maxzoom":         22,
            "color_class":     layer.color_class or "text-blue-600",
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
