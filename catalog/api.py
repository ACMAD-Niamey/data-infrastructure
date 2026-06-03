from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from catalog.models import HazardCategory, ProjectPage
from catalog.serializers import UILayersResponseSerializer
from catalog.ui_layers import dataset_entries_for_project, dataset_to_api_dict


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
