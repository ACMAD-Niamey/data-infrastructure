from __future__ import annotations

import re

from django import forms

_HEX6 = re.compile(r"^#[0-9a-fA-F]{6}$")


def hex_for_color_input(value: str | None) -> str:
    """Map stored #RRGGBB (or empty) to a value valid for input type=color."""
    if not value:
        return "#000000"
    s = str(value).strip()
    if s.startswith("#") and len(s) >= 7 and _HEX6.match(s[:7]):
        return s[:7].lower()
    return "#000000"


class HexColorWidget(forms.TextInput):
    """Swatch + native color picker synced with a #RRGGBB text field."""

    template_name = "catalog/widgets/hex_color.html"

    class Media:
        css = {"all": ("catalog/css/hex_color_widget.css",)}
        js = ("catalog/js/hex_color_widget.js",)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["picker_value"] = hex_for_color_input(value)
        return context
