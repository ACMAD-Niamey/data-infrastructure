from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping
from typing import Any, Union

from catalog.style.normalize import normalize_tile_params, split_tile_params

ColormapResult = Union[str, dict[str, Any]]


def compose_titiler_tilejson_params(
    http_url: str | None,
    tile_matrix_id: str,
    color_map_json: str = "",
    band_visualization_params: str | None = None,
    extra_params: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build query params for TiTiler ``/cog/.../tilejson.json`` (uses ``colormap``, not ``color_map``)."""
    params: dict[str, str] = {
        "url": http_url or "",
        "tile_format": "png",
        "tileMatrixSetId": tile_matrix_id,
    }
    if color_map_json:
        params["colormap"] = color_map_json
    if extra_params:
        params.update(extra_params)
    if band_visualization_params:
        fragment = band_visualization_params.strip()
        if fragment.startswith("&"):
            fragment = fragment[1:]
        for key, value in urllib.parse.parse_qsl(fragment, keep_blank_values=True):
            params[key] = value
    return params


def hex_to_rgb(hex_color: str) -> list[int]:
    h = hex_color.lstrip("#")
    if len(h) == 8:
        h = h[2:]
    if len(h) != 6:
        raise ValueError(f"Expected #RRGGBB hex, got {hex_color!r}")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)]


def build_discrete_colormap_json(style: dict[str, Any]) -> str:
    palette = style["palette"]
    values = style.get("values")
    color_map: dict[float | int, list[int]] = {}
    if values is not None:
        for i, v in enumerate(values):
            color_map[float(v)] = hex_to_rgb(palette[i])
    else:
        max_value = int(style.get("max", 0))
        for i in range(max_value):
            color_map[i + 1] = hex_to_rgb(palette[i])
    return json.dumps(color_map)


def build_linear_colormap_json(style: dict[str, Any]) -> str:
    values = style["values"]
    palette = style["palette"]
    min_value = float(style.get("min", 0))
    color_map: list[tuple[list[float], list[int]]] = []
    color_map.append(([min_value, float(values[0])], hex_to_rgb(palette[0])))
    for i in range(len(values) - 1):
        val_range = [float(values[i]), float(values[i + 1])]
        color_map.append((val_range, hex_to_rgb(palette[i + 1])))
    return json.dumps(color_map)


def build_colormap_for_titiler(tile_params: dict[str, Any] | None) -> ColormapResult:
    """
    Build TiTiler ``colormap`` JSON string, or a dict with ``band_visualization_params``
    for the band scheme. Raises ValueError if invalid.
    """
    if not tile_params:
        return ""
    merged = normalize_tile_params(tile_params)
    style, _ = split_tile_params(merged)
    scheme = style.get("scheme")
    if not scheme:
        return ""
    if scheme == "linear":
        return build_linear_colormap_json(style)
    if scheme == "discrete":
        return build_discrete_colormap_json(style)
    if scheme == "band":
        bvp = style.get("band_visualization_params")
        if not bvp:
            raise ValueError("band scheme requires band_visualization_params")
        return {"band_visualization_params": bvp}
    raise ValueError(f"Unknown scheme: {scheme!r}")


def titiler_extra_query_params(extras: dict[str, Any]) -> dict[str, str]:
    """
    Flatten extra tile_params for TiTiler query string.
    Lists/tuples are joined with commas where appropriate (e.g. rescale).
    """
    out: dict[str, str] = {}
    for key, val in extras.items():
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            out[key] = ",".join(str(x) for x in val)
        elif isinstance(val, bool):
            out[key] = "true" if val else "false"
        elif isinstance(val, dict):
            out[key] = json.dumps(val)
        else:
            out[key] = str(val)
    return out
