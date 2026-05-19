from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def parse_sld_raster_colormap(xml_text: str) -> dict[str, Any]:
    """
    Parse SLD RasterSymbolizer ColorMap into canonical tile_params (discrete scheme).

    Expects ColorMapEntry elements with ``quantity`` and ``color`` (#RRGGBB or #AARRGGBB).
    Switch to a linear scheme in the admin if your ramp should interpolate intervals.
    """
    root = ET.fromstring(xml_text.strip())
    entries: list[tuple[float, str]] = []

    for el in root.iter():
        if _local(el.tag) != "ColorMapEntry":
            continue
        qty = el.get("quantity")
        color = el.get("color") or el.get("Colour")
        if qty is None or not color:
            continue
        try:
            q = float(qty)
        except ValueError:
            continue
        entries.append((q, color.strip()))

    if not entries:
        raise ValueError("SLD: no ColorMapEntry with quantity and color found")

    entries.sort(key=lambda x: x[0])
    quantities = [q for q, _ in entries]
    palette = [c for _, c in entries]

    return {
        "scheme": "discrete",
        "values": quantities,
        "palette": palette,
        "min": min(quantities),
        "max": max(quantities),
    }
