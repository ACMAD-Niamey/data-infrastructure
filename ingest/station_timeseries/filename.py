"""Derive the official sensor id and exposure from a logger file name."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import EXPOSURE_BY_LABEL

# e.g. "Capteur 002 Soleil.CSV", "Capteur 004 (Ombre).csv"
_FILENAME_RE = re.compile(
    r"capteur\s*(?P<number>\d+)\s*\(?\s*(?P<label>soleil|ombre)?\s*\)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SensorIdentity:
    sensor_number: str  # zero-padded as printed on the device, e.g. "002"
    exposure: str | None  # "sun" | "shade" | None when the name does not say

    @property
    def station_code(self) -> str:
        # The printed sensor number is the only identifier the field teams
        # use, so it is the official id.
        return f"CAPTEUR-{self.sensor_number}"


def parse_sensor_filename(path: str | Path) -> SensorIdentity:
    """Raise ValueError when the name carries no sensor number: without an id
    we cannot tell which station the rows belong to."""
    stem = Path(path).stem
    match = _FILENAME_RE.search(stem)
    if not match:
        raise ValueError(f"Cannot read a sensor number from file name '{stem}'")
    label = (match.group("label") or "").lower()
    return SensorIdentity(
        sensor_number=match.group("number").zfill(3),
        exposure=EXPOSURE_BY_LABEL.get(label),
    )


def folder_context(path: str | Path) -> dict[str, str]:
    """Group / commune from the campaign folder layout
    ``<group>/<commune>/<sensor dir>/<file>``; empty when the layout differs."""
    parts = Path(path).resolve().parts
    if len(parts) < 4:
        return {}
    return {"group": parts[-4], "commune": parts[-3]}
