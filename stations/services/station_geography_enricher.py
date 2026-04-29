from __future__ import annotations

import logging
from dataclasses import dataclass
from time import sleep
import unicodedata

import requests
from django.db import connection
try:
    import pycountry
except ImportError:  # pragma: no cover - fallback for minimal runtime environments
    pycountry = None

from stations.models import CountryBoundary, Station

log = logging.getLogger(__name__)


@dataclass
class StationGeographyUpdate:
    canonical_code: str | None = None
    country_name: str | None = None
    admin1: str | None = None
    admin2: str | None = None


class StationGeographyEnricher:
    """
    Enrich station geography once during station create/update.

    Canonical strategy (must stay aligned with the bulk
    ``enrich_country_from_boundaries`` path and the
    ``sync_station_canonical_code`` management command):
      - ``Station.canonical_code`` is set verbatim from the spatially-intersecting
        ``country_boundaries.country_code`` (the layer's own code, which may be
        numeric e.g. ``133``, ``40765``). No ISO3 derivation or pycountry lookup
        is applied here, so MQTT-ingested stations match what the bulk command
        writes. If no boundary intersects, ``canonical_code`` is left untouched.
      - ``Station.country_code`` (the MQTT/ISO field) is never modified by this
        service.

    Country/admin name resolution:
      1) Country name from the intersecting boundary's ``country_name``.
      2) Otherwise Nominatim reverse geocode (also fills ``admin1`` / ``admin2``).
      3) Otherwise existing ``Station.country_name``.
      4) Final fallback: ISO3 ``Station.country_code`` -> country name via pycountry.
    """

    def __init__(self, *, timeout: int = 8, throttle_s: float = 1.0) -> None:
        self.timeout = timeout
        self.throttle_s = throttle_s

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if not value:
            return None
        normalized = unicodedata.normalize("NFKC", value).strip()
        normalized = " ".join(normalized.split())
        return normalized or None

    @staticmethod
    def _iso3_to_country_name(iso3: str | None) -> str | None:
        if not iso3:
            return None
        if pycountry is None:
            return None
        country = pycountry.countries.get(alpha_3=iso3.upper())
        return country.name if country else None

    @staticmethod
    def _to_iso3(country_code: str | None) -> str | None:
        if not country_code:
            return None
        cleaned = country_code.strip().upper()
        if not cleaned:
            return None
        if pycountry is None:
            return cleaned if len(cleaned) == 3 else None
        if len(cleaned) == 3:
            match = pycountry.countries.get(alpha_3=cleaned)
            return cleaned if match else None
        if len(cleaned) == 2:
            match = pycountry.countries.get(alpha_2=cleaned)
            return match.alpha_3 if match else None
        return None

    @staticmethod
    def _boundary_for_station(station: Station) -> CountryBoundary | None:
        if not station.geom:
            return None
        return (
            CountryBoundary.objects
            .filter(geom__intersects=station.geom)
            .exclude(country_name__isnull=True)
            .first()
        )

    def _reverse_geocode(self, lat: float, lon: float) -> dict | None:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "format": "jsonv2",
                    "lat": lat,
                    "lon": lon,
                    "zoom": 10,
                    "addressdetails": 1,
                    "accept-language": "en",
                },
                headers={
                    "User-Agent": "geomgr-station-enricher/1.0",
                    "Accept-Language": "en",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            log.warning("Nominatim reverse geocode failed for (%s, %s): %s", lat, lon, exc)
            return None
        finally:
            # Be a good Nominatim citizen.
            sleep(self.throttle_s)

    def enrich_country_from_boundaries(
        self,
        *,
        station_ids: list[int] | None = None,
        persist: bool = True,
        only_missing: bool = True,
    ) -> dict[str, int]:
        id_sql = ""
        params: list = []
        if station_ids:
            id_sql = " AND s.id = ANY(%s)"
            params.append(station_ids)

        missing_sql = ""
        if only_missing:
            missing_sql = (
                " AND ((s.country_name IS NULL OR TRIM(s.country_name) = '')"
                " OR (s.canonical_code IS NULL OR TRIM(s.canonical_code) = ''))"
            )

        count_sql = f"""
            SELECT COUNT(*)
            FROM stations s
            WHERE s.geom IS NOT NULL
            {missing_sql}
            {id_sql}
        """
        with connection.cursor() as cur:
            cur.execute(count_sql, params)
            candidate_count = int(cur.fetchone()[0] or 0)

        if not persist:
            return {"candidates": candidate_count, "updated": candidate_count}

        update_sql = f"""
            UPDATE stations AS s
            SET country_name = COALESCE(NULLIF(TRIM(s.country_name), ''), cb.country_name),
                canonical_code = COALESCE(NULLIF(TRIM(cb.country_code), ''), s.canonical_code),
                updated_at = NOW()
            FROM country_boundaries AS cb
            WHERE s.geom IS NOT NULL
              {missing_sql}
              {id_sql}
              AND ST_Intersects(s.geom::geometry, cb.geom)
        """
        with connection.cursor() as cur:
            cur.execute(update_sql, params)
            updated_count = int(cur.rowcount or 0)

        return {"candidates": candidate_count, "updated": updated_count}

    def enrich_station_geography(
        self,
        station: Station,
        *,
        persist: bool = True,
    ) -> dict[str, str | None]:
        update = StationGeographyUpdate()

        boundary = self._boundary_for_station(station)
        if boundary:
            boundary_code = (boundary.country_code or "").strip() or None
            if boundary_code:
                update.canonical_code = boundary_code
            if boundary.country_name:
                update.country_name = self._clean_text(boundary.country_name)

        # Nominatim-first when coordinates exist.
        if station.geom:
            payload = self._reverse_geocode(station.geom.y, station.geom.x)
            address = payload.get("address", {}) if payload else {}
            nominatim_country = self._clean_text(address.get("country"))
            nominatim_admin1 = self._clean_text(
                address.get("state")
                or address.get("region")
                or address.get("county")
            )
            nominatim_admin2 = self._clean_text(
                address.get("county")
                or address.get("city_district")
                or address.get("municipality")
            )
            if nominatim_country and not update.country_name:
                update.country_name = nominatim_country
            if nominatim_admin1:
                update.admin1 = nominatim_admin1
            if nominatim_admin2:
                update.admin2 = nominatim_admin2

        if not update.country_name:
            update.country_name = self._clean_text(
                station.country_name or self._iso3_to_country_name(station.country_code)
            )

        update_fields: list[str] = []
        existing_canonical = (station.canonical_code or "").strip() or None
        if update.canonical_code and update.canonical_code != existing_canonical:
            station.canonical_code = update.canonical_code
            update_fields.append("canonical_code")
        if update.country_name and update.country_name != self._clean_text(station.country_name):
            station.country_name = update.country_name
            update_fields.append("country_name")
        if update.admin1 and update.admin1 != self._clean_text(station.admin1):
            station.admin1 = update.admin1
            update_fields.append("admin1")
        if update.admin2 and update.admin2 != self._clean_text(station.admin2):
            station.admin2 = update.admin2
            update_fields.append("admin2")

        if persist and update_fields:
            update_fields.append("updated_at")
            station.save(update_fields=update_fields)

        return {
            "canonical_code": station.canonical_code,
            "country_name": station.country_name,
            "admin1": station.admin1,
            "admin2": station.admin2,
        }

