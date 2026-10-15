"""Reverse-geocode a station position into a human place name (Nominatim)."""

from __future__ import annotations

import logging
from time import sleep
from typing import Protocol

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Neighbourhood-level detail first: sensors in one commune would otherwise all
# be named just "Niamey". Order is most to least specific.
_PLACE_KEYS = (
    "neighbourhood", "quarter", "suburb", "city_district", "hamlet", "village",
)
_CITY_KEYS = ("city", "town", "municipality", "county")


class Geocoder(Protocol):
    def place_name(self, lat: float, lon: float) -> str | None: ...


class NominatimGeocoder:
    """Cached, throttled reverse geocoder.

    Nominatim's usage policy allows ~1 request/second and requires an
    identifying User-Agent, hence the throttle. Results are cached on rounded
    coordinates because a sun/shade pair sits a few metres apart and should
    resolve to the same place with one request.
    """

    def __init__(self, *, timeout: int = 8, throttle_s: float = 1.0) -> None:
        self.timeout = timeout
        self.throttle_s = throttle_s
        self._cache: dict[tuple[float, float], str | None] = {}

    def place_name(self, lat: float, lon: float) -> str | None:
        key = (round(lat, 3), round(lon, 3))
        if key not in self._cache:
            self._cache[key] = self._lookup(lat, lon)
        return self._cache[key]

    def _lookup(self, lat: float, lon: float) -> str | None:
        try:
            response = requests.get(
                NOMINATIM_URL,
                params={
                    "format": "jsonv2", "lat": lat, "lon": lon, "zoom": 16,
                    "addressdetails": 1, "accept-language": "en",
                },
                headers={"User-Agent": "geomgr-station-timeseries/1.0"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self.name_from_address(response.json().get("address") or {})
        except Exception as exc:  # noqa: BLE001 - naming is best-effort
            logger.warning("Nominatim lookup failed for (%s, %s): %s", lat, lon, exc)
            return None
        finally:
            sleep(self.throttle_s)

    @staticmethod
    def name_from_address(address: dict) -> str | None:
        place = next((address[k] for k in _PLACE_KEYS if address.get(k)), None)
        city = next((address[k] for k in _CITY_KEYS if address.get(k)), None)
        if place and city and place != city:
            return f"{place}, {city}"
        return place or city
