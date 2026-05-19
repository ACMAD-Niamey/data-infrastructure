from __future__ import annotations

import copy
import re
from typing import Any

# Keys that define raster styling; everything else is passed through to TiTiler (rescale, nodata, bidx, …)
STYLE_KEYS = frozenset(
    {
        "scheme",
        "min",
        "max",
        "values",
        "palette",
        "band_visualization_params",
    }
)

_SCHEME_ALIASES = {
    "descrete": "discrete",
    "discrete": "discrete",
    "linear": "linear",
    "band": "band",
}


def _normalize_hex(color: str) -> str:
    s = (color or "").strip()
    if not s:
        return ""
    if s.startswith("#"):
        h = s[1:]
    else:
        h = s
    if len(h) == 8:
        h = h[2:]
    if len(h) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"Invalid hex color: {color!r}")
    return f"#{h.lower()}"


def normalize_tile_params(raw: dict[str, Any] | None) -> dict[str, Any]:
    """
    Canonicalize scheme spelling, validate discrete value/palette lengths, normalize hex colors.
    Unknown keys are preserved for TiTiler passthrough (rescale, nodata, bidx, …).
    """
    if not raw:
        return {}
    out = copy.deepcopy(raw)

    scheme = None
    scheme_raw = out.get("scheme")
    if scheme_raw is not None:
        key = str(scheme_raw).strip().lower()
        if key not in _SCHEME_ALIASES:
            raise ValueError(f"Unknown scheme: {scheme_raw!r}")
        out["scheme"] = _SCHEME_ALIASES[key]
        scheme = out["scheme"]
    palette_in = out.get("palette")
    if palette_in is not None:
        palette: list[str] = []
        for c in palette_in:
            palette.append(_normalize_hex(str(c)))
        out["palette"] = palette

    values_in = out.get("values")
    if values_in is not None:
        out["values"] = [float(v) for v in values_in]

    if scheme == "discrete" and out.get("palette"):
        plen = len(out["palette"])
        if out.get("values") is not None:
            if len(out["values"]) != plen:
                raise ValueError(
                    f"discrete scheme: len(values) ({len(out['values'])}) must match len(palette) ({plen})"
                )
        elif out.get("max") is not None:
            mx = int(out["max"])
            if plen != mx:
                raise ValueError(
                    f"discrete scheme without values: len(palette) ({plen}) must equal max ({mx})"
                )

    if scheme == "linear":
        if out.get("values") is None:
            raise ValueError("linear scheme requires values")
        if out.get("palette") is None:
            raise ValueError("linear scheme requires palette")
        if len(out["palette"]) != len(out["values"]):
            raise ValueError(
                f"linear scheme: len(palette) ({len(out['palette'])}) must match len(values) ({len(out['values'])})"
            )

    return out


def split_tile_params(
    raw: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split merged tile_params into style dict and extra TiTiler query keys."""
    if not raw:
        return {}, {}
    style: dict[str, Any] = {}
    extras: dict[str, Any] = {}
    for k, v in raw.items():
        if k in STYLE_KEYS:
            style[k] = v
        else:
            extras[k] = v
    return style, extras
