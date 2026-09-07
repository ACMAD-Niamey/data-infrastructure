"""Register the combined drought forecast datasets + layer styles.

Creates (idempotently) two raster ``DatasetPage``s under a project and their
``Layer`` style snippets, matching the class raster the ``adma_data_pipeline``
forecast-combine job publishes to MinIO + pgSTAC:

    combined_drought_forecast_era5   (CDI reference = ERA5)
    combined_drought_forecast_gpcc   (CDI reference = GPCC)

The **palette + legend are pulled from the Africa Drought Advisory backend**
(``GET {DROUGHT_BACKEND_URL}/api/data_api/rs_data/get_layer_style?key=``) so the
CMS-editable ``LayerStyle`` there stays the single source of truth. The bundled
``FALLBACK_PALETTE`` is used only when that fetch fails (or ``--offline``).

Both datasets share the ``seasonal`` cadence. Run once per environment; re-runs
update the datasets + styles in place.

    python manage.py register_combined_forecast_layers --project multi-hazard --icon-slug drought
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

#: Style key to look up in the drought backend (one style, shared by both grids).
STYLE_KEY = "combined_forecast"

#: Fallback only. Keep in sync with the backend ``LayerStyle`` "combined_forecast"
#: (ColorBrewer RdBu, reversed: wet = blue, dry = red). Class 0 = NoData.
FALLBACK_PALETTE = {
    1: ("#2166ac", "Full-confidence wetter"),
    2: ("#67a9cf", "Leaning wetter"),
    3: ("#f7f7f7", "Near-normal / conflicting"),
    4: ("#ef8a62", "Leaning drier"),
    5: ("#b2182b", "Full-confidence drier"),
}

DATASETS = [
    {
        "dataset_id": "combined_drought_forecast_era5",
        "title": "Combined drought forecast (ERA5)",
        "resolution": "~1° (ERA5 CDI grid)",
        "description": (
            "Seasonal signed drought forecast fusing the ACMAD rainfall tercile "
            "forecast with the Copernicus UNWDC forecast, on the ERA5 CDI grid."
        ),
    },
    {
        "dataset_id": "combined_drought_forecast_gpcc",
        "title": "Combined drought forecast (GPCC)",
        "resolution": "~1° (GPCC CDI grid)",
        "description": (
            "Seasonal signed drought forecast fusing the ACMAD rainfall tercile "
            "forecast with the Copernicus UNWDC forecast, on the GPCC CDI grid."
        ),
    },
]


def _fallback_style() -> dict:
    """Normalized style dict built from :data:`FALLBACK_PALETTE`."""
    codes = sorted(FALLBACK_PALETTE)
    return {
        "scheme": "discrete",
        "opacity": 0.9,
        "min": float(codes[0]),
        "max": float(codes[-1]),
        "legend": {FALLBACK_PALETTE[c][1]: FALLBACK_PALETTE[c][0] for c in codes},
        "stops": [(float(c), FALLBACK_PALETTE[c][0]) for c in codes],
        "source": "fallback",
    }


def _normalize_backend_style(data: dict) -> dict | None:
    """Map a ``get_layer_style`` response to our normalized style dict.

    Returns ``None`` if the payload has nothing usable (caller falls back).
    """
    legend_list = data.get("legend") or []
    tile_params = data.get("tile_params") or {}
    values = tile_params.get("values")
    palette = tile_params.get("palette")

    if values and palette and len(values) == len(palette):
        stops = [(float(v), str(c)) for v, c in zip(values, palette)]
    else:  # derive from the ordered legend (1-based position = class code)
        stops = [
            (float(i + 1), e["color"])
            for i, e in enumerate(legend_list)
            if e.get("color")
        ]
    if not stops:
        return None

    legend = {
        e["label"]: e["color"]
        for e in legend_list
        if e.get("color") and e.get("label")
    }
    if not legend:
        legend = {str(int(v)): c for v, c in stops}

    return {
        "scheme": data.get("scheme") or tile_params.get("scheme") or "discrete",
        "opacity": float(data.get("opacity", 0.9) or 0.9),
        "min": float(tile_params.get("min", stops[0][0])),
        "max": float(tile_params.get("max", stops[-1][0])),
        "legend": legend,
        "stops": stops,
        "source": "backend",
    }


def _fetch_style(key: str, *, offline: bool = False, timeout: float = 10.0) -> dict:
    """Pull the canonical style from the drought backend; fall back on any error."""
    if offline:
        return _fallback_style()

    base = getattr(settings, "DROUGHT_BACKEND_URL", "").rstrip("/")
    if not base:
        logger.warning("DROUGHT_BACKEND_URL not set — using fallback palette")
        return _fallback_style()

    url = f"{base}/api/data_api/rs_data/get_layer_style"
    try:
        resp = requests.get(url, params={"key": key}, timeout=timeout)
        resp.raise_for_status()
        normalized = _normalize_backend_style(resp.json())
    except (requests.RequestException, ValueError) as exc:
        logger.warning("get_layer_style(%s) failed (%s) — using fallback palette", key, exc)
        return _fallback_style()

    if normalized is None:
        logger.warning("get_layer_style(%s) had no usable palette — using fallback", key)
        return _fallback_style()
    return normalized


class Command(BaseCommand):
    help = "Register the combined_drought_forecast_{era5,gpcc} datasets + layer styles."

    def add_arguments(self, parser):
        parser.add_argument("--project", default="multi-hazard", help="ProjectPage slug.")
        parser.add_argument("--hazard-key", default="drought", help="HazardCategory key.")
        parser.add_argument("--icon-slug", default="", help="Existing LayerIcon slug to assign.")
        parser.add_argument("--style-key", default=STYLE_KEY, help="Drought-backend get_layer_style key.")
        parser.add_argument("--offline", action="store_true", help="Skip the backend fetch; use FALLBACK_PALETTE.")
        parser.add_argument("--publish", action="store_true", help="Publish the dataset pages.")

    @transaction.atomic
    def handle(self, *args, **opts):
        from catalog.models import (
            DatasetPage, HazardCategory, Layer, LayerColorStop, LayerIcon, ProjectPage,
        )

        project = ProjectPage.objects.filter(slug=opts["project"]).first()
        if not project:
            self.stderr.write(self.style.ERROR(f"No ProjectPage with slug '{opts['project']}'"))
            return

        hazard, _ = HazardCategory.objects.get_or_create(
            key=opts["hazard_key"], defaults={"label": opts["hazard_key"].title()}
        )
        icon = None
        if opts["icon_slug"]:
            icon = LayerIcon.objects.filter(slug=opts["icon_slug"]).first()
            if not icon:
                self.stderr.write(self.style.WARNING(f"No LayerIcon '{opts['icon_slug']}' — leaving icon unset"))

        style = _fetch_style(opts["style_key"], offline=opts["offline"])
        self.stdout.write(
            f"style source: {style['source']} "
            f"({len(style['stops'])} stops, scheme={style['scheme']})"
        )

        for spec in DATASETS:
            page = DatasetPage.objects.filter(dataset_id=spec["dataset_id"]).first()
            if page is None:
                page = DatasetPage(
                    title=spec["title"],
                    slug=spec["dataset_id"].replace("_", "-"),
                    dataset_id=spec["dataset_id"],
                    dataset_type="raster",
                    cadence="seasonal",
                    stac_collection_id=spec["dataset_id"],
                    hazard_category=hazard,
                    icon=icon,
                    is_published_for_ui=True,
                    description=spec["description"],
                )
                project.add_child(instance=page)
                created = True
            else:
                page.title = spec["title"]
                page.dataset_type = "raster"
                page.cadence = "seasonal"
                page.stac_collection_id = spec["dataset_id"]
                page.hazard_category = hazard
                if icon:
                    page.icon = icon
                page.is_published_for_ui = True
                page.description = spec["description"]
                page.save()
                created = False

            rev = page.save_revision()
            if opts["publish"]:
                rev.publish()

            # Key on layer_id (unique) so this works whether Layer.dataset is a
            # OneToOne or a FK (the multi-style refactor). One style per dataset.
            layer, _ = Layer.objects.update_or_create(
                layer_id=spec["dataset_id"],
                defaults={
                    "dataset": page,
                    "title": f"{spec['title']} — style",
                    "layer_type": "raster",
                    "style_scheme": style["scheme"],
                    "style_min": style["min"],
                    "style_max": style["max"],
                    "use_advanced_tile_params": False,
                    "opacity": style["opacity"],
                    "minzoom": 0,
                    "maxzoom": 12,
                    "legend": style["legend"],
                    "coverage": "Africa",
                    "resolution": spec["resolution"],
                    "update_frequency": "Seasonal (rolling 3-month)",
                    "source_organization": "ACMAD / Africa Drought System",
                    "legend_description": (
                        "1–5 signed forecast class: wetter (blue) → near-normal → drier (red)."
                    ),
                },
            )
            layer.color_stops.all().delete()
            for i, (value, color) in enumerate(style["stops"]):
                LayerColorStop.objects.create(
                    layer=layer, sort_order=i, value=value, color=color,
                )
            layer.refresh_from_db()
            layer.sync_tile_params_from_stops()

            self.stdout.write(self.style.SUCCESS(
                f"{'created' if created else 'updated'} {spec['dataset_id']} "
                f"(page id={page.id}, style id={layer.id})"
            ))

        self.stdout.write(self.style.SUCCESS(
            "Done. Assign a LayerIcon in Wagtail admin if not set, then verify "
            f"GET /api/catalog/ui/layers?project={opts['project']}"
        ))
