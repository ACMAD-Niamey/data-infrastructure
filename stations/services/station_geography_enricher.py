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

    Strategy:
    1) Nominatim reverse geocode first (if coordinates exist) for canonical names.
    2) Static ISO3 mapping as fallback for country_name.
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
            boundary_code = self._to_iso3(boundary.country_code)
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

        canonical_station_code = self._to_iso3(station.canonical_code)
        if not update.canonical_code and canonical_station_code:
            update.canonical_code = canonical_station_code

        # Resilient fallback for canonical country code/name.
        if not update.canonical_code and station.country_name and pycountry is not None:
            match = pycountry.countries.get(name=station.country_name.strip())
            if match:
                update.canonical_code = match.alpha_3
        if not update.country_name:
            update.country_name = self._clean_text(
                station.country_name or self._iso3_to_country_name(update.canonical_code or station.canonical_code)
            )

        update_fields: list[str] = []
        if update.canonical_code and update.canonical_code != self._to_iso3(station.canonical_code):
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

