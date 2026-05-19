from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def parse_qml_raster_pseudocolor(xml_text: str) -> dict[str, Any]:
    """
    Parse QGIS raster singleband pseudocolor legend items into canonical tile_params.

    Looks for ``item`` elements with ``value`` and ``color`` under a raster renderer.
    """
    root = ET.fromstring(xml_text.strip())
    items: list[tuple[float, str]] = []

    for el in root.iter():
        if _local(el.tag) != "item":
            continue
        if el.get("alpha") == "-1":
            continue
        val = el.get("value")
        color = el.get("color")
        if val is None or color is None:
            continue
        try:
            v = float(val)
        except ValueError:
            continue
        color = color.strip()
        if not re.match(r"^#?[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$", color.replace("#", "", 1)):
            continue
        if not color.startswith("#"):
            color = f"#{color}"
        items.append((v, color))

    if not items:
        raise ValueError(
            "QML: no raster pseudocolor items found (expected item elements with value/color)"
        )

    items.sort(key=lambda x: x[0])
    values = [v for v, _ in items]
    palette = [c for _, c in items]

    return {
        "scheme": "discrete",
        "values": values,
        "palette": palette,
        "min": min(values),
        "max": max(values),
    }
