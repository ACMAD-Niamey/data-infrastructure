"""Build UI layer payloads for the catalog layers API."""

from __future__ import annotations

from typing import NamedTuple

from django.utils import timezone
from django.utils.html import strip_tags
from wagtail.rich_text import expand_db_html

from catalog.models import DatasetPage, Layer, ProjectPage

DEFAULT_UI = {
    "default_visible": False,
    "opacity": 0.85,
    "minzoom": 0,
    "maxzoom": 12,
}


def _description_raw_html(description) -> str:
    """RichTextField may be a RichText object (.source) or a plain str in DB."""
    if not description:
        return ""
    if hasattr(description, "source"):
        return description.source or ""
    return str(description)


def dataset_description_payload(dataset: DatasetPage) -> dict[str, str]:
    raw_html = _description_raw_html(dataset.description)
    if not raw_html:
        return {"html": "", "plain": ""}
    html = expand_db_html(raw_html)
    plain = strip_tags(html).strip()
    return {"html": html, "plain": plain}


def icon_payload_from_dataset(dataset: DatasetPage, request) -> dict[str, str] | None:
    if not dataset.icon_id or not dataset.icon or not dataset.icon.image_id:
        return None
    file_url = dataset.icon.image.file.url
    url = request.build_absolute_uri(file_url) if request else file_url
    return {"slug": dataset.icon.slug, "url": url}


def _layer_type_for_dataset(dataset: DatasetPage, style: Layer | None) -> str:
    if style:
        return style.layer_type
    return dataset.dataset_type


def dataset_to_api_dict(dataset: DatasetPage, request, category_override: str | None = None) -> dict:
    style: Layer | None = getattr(dataset, "style_config", None)
    icon = icon_payload_from_dataset(dataset, request)

    if style:
        tile = {
            "template": style.tile_template or "",
            "params": style.tile_params or {},
        }
        ui = {
            "default_visible": style.default_visible,
            "opacity": style.opacity,
            "minzoom": style.minzoom,
            "maxzoom": style.maxzoom,
            "color_class": dataset.color_class or "text-blue-600",
        }
        legend = style.legend or {}
        updated_at = style.updated_at.isoformat()
    else:
        tile = {"template": "", "params": {}}
        ui = {
            **DEFAULT_UI,
            "color_class": dataset.color_class or "text-blue-600",
        }
        legend = {}
        if getattr(dataset, "last_published_at", None):
            updated_at = dataset.last_published_at.isoformat()
        else:
            updated_at = timezone.now().isoformat()

    details = {
        "coverage":            style.coverage or "Africa",
        "resolution":          style.resolution or "",
        "update_frequency":    style.update_frequency or "",
        "source_organization": style.source_organization or "",
        "methodology_html":    expand_db_html(_description_raw_html(style.methodology)),
        "methodology_url":     style.methodology_url or "",
    } if style else None

    return {
        "id": dataset.dataset_id,
        "title": dataset.title,
        "type": _layer_type_for_dataset(dataset, style),
        "project": dataset.get_parent().slug if dataset.get_parent() else None,
        "hazard_category": (
            dataset.hazard_category.key if dataset.hazard_category_id else category_override
        ),
        "details": details,
        "description": dataset_description_payload(dataset),
        "icon": icon,
        "dataset": {
            "id": dataset.dataset_id,
            "title": dataset.title,
            "cadence": dataset.cadence,
            "dataset_type": dataset.dataset_type,
            "stac_collection": dataset.stac_collection_id or dataset.dataset_id,
        },
        "selection": {"cadence": dataset.cadence},
        "tile": tile,
        "ui": ui,
        "legend": legend,
        "updated_at": updated_at,
    }


def datasets_for_project(project_slug: str) -> list[DatasetPage]:
    project_page = ProjectPage.objects.live().get(slug=project_slug)
    return list(
        DatasetPage.objects.live()
        .child_of(project_page)
        .filter(is_published_for_ui=True, icon__isnull=False)
        .select_related("icon", "icon__image")
        .select_related("style_config")
        .select_related("hazard_category")
        .order_by("sort_order", "title")
    )


# Backwards-compatible alias for tests patching layers_for_project
def layers_for_project(project_slug: str) -> list[DatasetPage]:
    return datasets_for_project(project_slug)


class DatasetEntry(NamedTuple):
    dataset: DatasetPage
    category_override: str | None


def _dataset_qs(project_page: ProjectPage):
    return (
        DatasetPage.objects.live()
        .child_of(project_page)
        .filter(is_published_for_ui=True, icon__isnull=False)
        .select_related("icon", "icon__image", "style_config", "hazard_category")
        .order_by("sort_order", "title")
    )


def dataset_entries_for_project(project_slug: str) -> list[DatasetEntry]:
    """Like datasets_for_project but also pulls in included projects with category overrides."""
    project_page = ProjectPage.objects.live().get(slug=project_slug)

    entries: list[DatasetEntry] = [
        DatasetEntry(ds, None) for ds in _dataset_qs(project_page)
    ]

    for inc in project_page.inclusions.select_related("source_project", "default_category"):
        cat_key = inc.default_category.key if inc.default_category_id else None
        for ds in _dataset_qs(inc.source_project):
            entries.append(DatasetEntry(ds, cat_key))

    return entries
