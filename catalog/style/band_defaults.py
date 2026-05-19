from __future__ import annotations

from typing import Any

from catalog.style.normalize import split_tile_params

# TiTiler RGB compositing: red=band1, green=band2, blue=band3
DEFAULT_RGB_BAND_VISUALIZATION_PARAMS = "bidx=1&bidx=2&bidx=3"

def ensure_band_tile_params(tile_params: dict[str, Any] | None) -> dict[str, Any]:
    """
    Normalize tile_params for band (RGB) visualization.

    - Sets scheme to ``band``
    - Fills default ``band_visualization_params`` when missing
    - Drops pseudocolor keys (values/palette/min/max); keeps TiTiler extras (rescale, nodata, …)
    """
    style, extras = split_tile_params(tile_params or {})
    bvp = style.get("band_visualization_params")
    if not bvp or not str(bvp).strip():
        bvp = DEFAULT_RGB_BAND_VISUALIZATION_PARAMS

    band_style: dict[str, Any] = {
        "scheme": "band",
        "band_visualization_params": str(bvp).strip(),
    }
    return {**band_style, **extras}
