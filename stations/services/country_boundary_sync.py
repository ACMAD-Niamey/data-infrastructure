from __future__ import annotations

import json
import os
from dataclasses import dataclass

import requests
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon

from stations.models import CountryBoundary


@dataclass
class CountryBoundarySyncResult:
    fetched: int = 0
    upserted: int = 0
    skipped: int = 0


class CountryBoundarySyncService:
    def __init__(self, *, timeout_s: int = 30) -> None:
        self.timeout_s = timeout_s
        self.wfs_url = os.environ.get("GEOSERVER_COUNTRY_WFS_URL", "https://ada.acmad.org/geoserver/wfs?request=GetFeature&service=WFS&version=1.0.0&typeName=africa_drought_datasets:data_api_adminlevelzero&outputFormat=application/json").strip() # 

    @staticmethod
    def _first(props: dict, keys: list[str]) -> str | None:
        for key in keys:
            value = props.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _first_code(props: dict, keys: list[str]) -> str | None:
        """Return the first non-empty value for *keys* coerced to a string.

        The WFS layer publishes ``country_code`` as a numeric value (e.g. ``90``),
        so we need to accept ints/floats in addition to strings and emit a
        normalized 3-char-max string suitable for ``country_boundaries.country_code``.
        """
        for key in keys:
            value = props.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return str(value)
            if isinstance(value, float):
                if value.is_integer():
                    return str(int(value))
                return str(value)
        return None

    @staticmethod
    def _as_multipolygon(geometry: dict) -> MultiPolygon | None:
        geom = GEOSGeometry(json.dumps(geometry), srid=4326)
        if isinstance(geom, MultiPolygon):
            return geom
        if isinstance(geom, Polygon):
            return MultiPolygon(geom, srid=4326)
        return None

    def fetch_features(self) -> list[dict]:
        if not self.wfs_url:
            raise ValueError("GEOSERVER_COUNTRY_WFS_URL is not set.")
        response = requests.get(self.wfs_url, timeout=self.timeout_s)
        response.raise_for_status()
        payload = response.json()
        return payload.get("features", [])

    def sync(self, *, persist: bool = True) -> CountryBoundarySyncResult:
        result = CountryBoundarySyncResult()
        for feature in self.fetch_features():
            result.fetched += 1
            props = feature.get("properties", {}) or {}
            geometry = feature.get("geometry")
            if not geometry:
                result.skipped += 1
                continue

            country_name = self._first(
                props,
                [
                    "country_name",
                    "name_en",
                    "NAME_EN",
                    "name",
                    "NAME",
                    "admin",
                    "ADMIN",
                    "sovereignt",
                    "SOVEREIGNT",
                ],
            )
            if not country_name:
                result.skipped += 1
                continue

            country_code = self._first_code(
                props,
                [
                    "country_code",
                    "COUNTRY_CODE",
                    "iso3",
                    "ISO3",
                    "iso_a3",
                    "ISO_A3",
                    "adm0_a3",
                    "ADM0_A3",
                ],
            )
            mpoly = self._as_multipolygon(geometry)
            if not mpoly:
                result.skipped += 1
                continue

            if persist:
                boundary, _ = CountryBoundary.objects.update_or_create(
                    country_name=country_name,
                    defaults={
                        "country_code": (country_code or None),
                        "geom": mpoly,
                        "source_feature_id": feature.get("id"),
                    },
                )
                boundary.update_bounds()
                boundary.save(update_fields=["country_bounds", "updated_at"])
            result.upserted += 1

        return result
