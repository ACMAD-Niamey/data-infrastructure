"""Register the combined drought forecast + hazard datasets and layer styles.

Creates (idempotently) four raster ``DatasetPage``s under a project and their
``Layer`` style snippets, matching the class rasters the ``adma_data_pipeline``
forecast-combine job publishes to MinIO + pgSTAC:

    combined_drought_forecast_era5   combined_drought_hazard_era5    (CDI reference = ERA5)
    combined_drought_forecast_gpcc   combined_drought_hazard_gpcc    (CDI reference = GPCC)

The **palette + legend are pulled from the Africa Drought Advisory backend**
(``GET {DROUGHT_BACKEND_URL}/api/data_api/rs_data/get_layer_style?key=``) —
``combined_forecast`` for the forecast pair, ``combined_hazard`` for the hazard
pair — so the CMS-editable ``LayerStyle`` there stays the single source of
truth. The bundled ``FALLBACK_PALETTE``s are used only when that fetch fails
(or ``--offline``).

All four datasets share the ``seasonal`` cadence. Run once per environment;
re-runs update the datasets + styles in place.

    python manage.py register_combined_forecast_layers --project multi-hazard --icon-slug drought
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

#: Fallback only, per style key. Keep in sync with the backend ``LayerStyle``
#: rows of the same key. Class 0 = NoData in both.
FALLBACK_PALETTES = {
    # ColorBrewer RdBu (5), reversed: wet = blue, dry = red.
    "combined_forecast": {
        1: ("#2166ac", "Full-confidence wetter"),
        2: ("#67a9cf", "Leaning wetter"),
        3: ("#f7f7f7", "Near-normal / conflicting"),
        4: ("#ef8a62", "Leaning drier"),
        5: ("#b2182b", "Full-confidence drier"),
    },
    # CDI-anchored 9-class hazard ramp (S = cdi_tier + forecast, 0..4 step 0.5).
    "combined_hazard": {
        1: ("#f5f5f5", "No drought hazard"),
        2: ("#fbfa86", "Very low"),
        3: ("#ffff01", "Low (Watch)"),
        4: ("#ffd001", "Low-moderate"),
        5: ("#ffa601", "Moderate (Warning)"),
        6: ("#ff5301", "Moderate-high"),
        7: ("#ff0000", "High (Alert)"),
        8: ("#d20a0b", "Very high"),
        9: ("#a50f15", "Extreme"),
    },
}

DATASETS = [
    {
        "dataset_id": "combined_drought_forecast_era5",
        "style_key": "combined_forecast",
        "title": "Combined drought forecast (ERA5)",
        "resolution": "~1° (ERA5 CDI grid)",
        "legend_description": "1-5 signed forecast class: wetter (blue) -> near-normal -> drier (red).",
        "description": (
            "Seasonal signed drought forecast fusing the ACMAD rainfall tercile "
            "forecast with the Copernicus UNWDC forecast, on the ERA5 CDI grid."
        ),
    },
    {
        "dataset_id": "combined_drought_forecast_gpcc",
        "style_key": "combined_forecast",
        "title": "Combined drought forecast (GPCC)",
        "resolution": "~1° (GPCC CDI grid)",
        "legend_description": "1-5 signed forecast class: wetter (blue) -> near-normal -> drier (red).",
        "description": (
            "Seasonal signed drought forecast fusing the ACMAD rainfall tercile "
            "forecast with the Copernicus UNWDC forecast, on the GPCC CDI grid."
        ),
    },
    {
        "dataset_id": "combined_drought_hazard_era5",
        "style_key": "combined_hazard",
        "title": "Combined monitoring & forecast hazard (ERA5)",
        "resolution": "~1° (ERA5 CDI grid)",
        "legend_description": (
            "9-class blended hazard S = CDI tier + forecast: 1 = no drought hazard, "
            "3 = Watch, 5 = Warning, 7 = Alert, 9 = extreme; 0 = NoData."
        ),
        "description": (
            "Combined monitoring & forecast hazard indicator (S = cdi_tier + forecast) "
            "fusing CDI drought monitoring with the combined ACMAD + UNWDC forecast, "
            "on the ERA5 CDI grid."
        ),
    },
    {
        "dataset_id": "combined_drought_hazard_gpcc",
        "style_key": "combined_hazard",
        "title": "Combined monitoring & forecast hazard (GPCC)",
        "resolution": "~1° (GPCC CDI grid)",
        "legend_description": (
            "9-class blended hazard S = CDI tier + forecast: 1 = no drought hazard, "
            "3 = Watch, 5 = Warning, 7 = Alert, 9 = extreme; 0 = NoData."
        ),
        "description": (
            "Combined monitoring & forecast hazard indicator (S = cdi_tier + forecast) "
            "fusing CDI drought monitoring with the combined ACMAD + UNWDC forecast, "
            "on the GPCC CDI grid."
        ),
    },
]


def _fallback_style(style_key: str) -> dict:
    """Normalized style dict built from :data:`FALLBACK_PALETTES`."""
    palette = FALLBACK_PALETTES[style_key]
    codes = sorted(palette)
    return {
        "scheme": "discrete",
        "opacity": 0.9,
        "min": float(codes[0]),
        "max": float(codes[-1]),
        "legend": {palette[c][1]: palette[c][0] for c in codes},
        "stops": [(float(c), palette[c][0]) for c in codes],
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
        return _fallback_style(key)

    base = getattr(settings, "DROUGHT_BACKEND_URL", "").rstrip("/")
    if not base:
        logger.warning("DROUGHT_BACKEND_URL not set — using fallback palette for %s", key)
        return _fallback_style(key)

    url = f"{base}/api/data_api/rs_data/get_layer_style"
    try:
        resp = requests.get(url, params={"key": key}, timeout=timeout)
        resp.raise_for_status()
        normalized = _normalize_backend_style(resp.json())
    except (requests.RequestException, ValueError) as exc:
        logger.warning("get_layer_style(%s) failed (%s) — using fallback palette", key, exc)
        return _fallback_style(key)

    if normalized is None:
        logger.warning("get_layer_style(%s) had no usable palette — using fallback", key)
        return _fallback_style(key)
    return normalized


class Command(BaseCommand):
    help = (
        "Register the combined_drought_forecast_{era5,gpcc} and "
        "combined_drought_hazard_{era5,gpcc} datasets + layer styles."
    )

    def add_arguments(self, parser):
        parser.add_argument("--project", default="multi-hazard", help="ProjectPage slug.")
        parser.add_argument("--hazard-key", default="drought", help="HazardCategory key.")
        parser.add_argument("--icon-slug", default="", help="Existing LayerIcon slug to assign.")
        parser.add_argument(
            "--style-key", default="",
            help="Override: use this get_layer_style key for every dataset "
                 "(default: each dataset's own style_key — combined_forecast / combined_hazard).",
        )
        parser.add_argument(
            "--dataset-id", action="append", default=[],
            help="Register only this dataset_id (repeatable). Default: all four.",
        )
        parser.add_argument("--offline", action="store_true", help="Skip the backend fetch; use the fallback palette.")
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

        wanted = set(opts["dataset_id"]) or None
        specs = [s for s in DATASETS if wanted is None or s["dataset_id"] in wanted]
        if not specs:
            self.stderr.write(self.style.ERROR(f"No dataset matches --dataset-id {sorted(wanted)}"))
            return

        # One backend fetch per distinct style key (forecast pair shares one, hazard pair another).
        style_cache: dict[str, dict] = {}

        def style_for(spec: dict) -> dict:
            key = opts["style_key"] or spec["style_key"]
            if key not in style_cache:
                style_cache[key] = _fetch_style(key, offline=opts["offline"])
                s = style_cache[key]
                self.stdout.write(
                    f"style '{key}' source: {s['source']} ({len(s['stops'])} stops, scheme={s['scheme']})"
                )
            return style_cache[key]

        for spec in specs:
            style = style_for(spec)
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
                    "legend_description": spec["legend_description"],
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
