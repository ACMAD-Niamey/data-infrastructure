from __future__ import annotations

import json
import re
from typing import Any

from django import forms

from catalog.widgets.hex_color import hex_for_color_input

_HEX6 = re.compile(r"^#[0-9a-fA-F]{6}$")

# Keys used by structured (continuous) legends — not label→color maps.
_STRUCTURED_KEYS = frozenset(
    {"type", "colors", "breaks", "label", "min", "max", "scheme", "palette", "values"}
)


def _is_hex_color(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX6.match(value.strip()))


def is_simple_name_color_legend(data: Any) -> bool:
    """True when legend is empty or a flat dict of label -> #RRGGBB."""
    if data is None or data == "":
        return True
    if not isinstance(data, dict):
        return False
    if not data:
        return True
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            return False
        if key in _STRUCTURED_KEYS:
            return False
        if not _is_hex_color(value):
            return False
    return True


def legend_to_entries(data: Any) -> list[dict[str, str]]:
    if data is None or data == "":
        return []
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return []
    if not isinstance(data, dict) or not is_simple_name_color_legend(data):
        return []
    return [
        {"name": str(name), "color": str(color).lower()}
        for name, color in data.items()
    ]


def entries_to_legend(entries: list[dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in entries:
        name = (entry.get("name") or "").strip()
        color = (entry.get("color") or "").strip()
        if not name or not _is_hex_color(color):
            continue
        out[name] = color.lower()
    return out


class LegendMapWidget(forms.Widget):
    """
    Edit legend as label → #RRGGBB rows (matches e-safari-ui renderLegend).
    Falls back to raw JSON for structured legends.
    """

    template_name = "catalog/widgets/legend_map.html"

    class Media:
        css = {
            "all": (
                "catalog/css/hex_color_widget.css",
                "catalog/css/legend_map_widget.css",
            )
        }
        js = (
            "catalog/js/hex_color_widget.js",
            "catalog/js/legend_map_widget.js",
        )

    def format_value(self, value: Any) -> str:
        if value is None or value == "":
            return "{}"
        if isinstance(value, dict):
            return json.dumps(value, separators=(",", ":"))
        if isinstance(value, str):
            return value
        return "{}"

    def value_from_datadict(self, data, files, name):
        """Return a JSON string — required by forms.JSONField.bound_data()."""
        raw = data.get(name, "{}")
        if not raw:
            return "{}"
        if isinstance(raw, dict):
            return json.dumps(raw, separators=(",", ":"))
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return "{}"
        if not isinstance(parsed, dict):
            return "{}"
        return json.dumps(parsed, separators=(",", ":"))

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        parsed_value = value
        if isinstance(value, str) and value:
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = {}

        simple = is_simple_name_color_legend(parsed_value)
        entries = legend_to_entries(parsed_value) if simple else []
        if not entries and simple:
            entries = [{"name": "", "color": "#000000"}]

        context["widget"]["entries"] = entries
        context["widget"]["advanced_mode"] = not simple
        context["widget"]["advanced_json"] = (
            json.dumps(parsed_value, indent=2)
            if isinstance(parsed_value, dict)
            else json.dumps({}, indent=2)
        )
        context["widget"]["json_value"] = self.format_value(parsed_value)
        for entry in context["widget"]["entries"]:
            entry["picker_value"] = hex_for_color_input(entry.get("color"))
        return context
