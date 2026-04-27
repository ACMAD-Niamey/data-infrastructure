"""Import WMO surface stations from the NOAA Integrated Surface Database (ISD).

Data source
-----------
https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv

CSV schema (comma-separated, first row is header)::

    USAF, WBAN, STATION NAME, CTRY, ST, CALL, LAT, LON, ELEV(M), BEGIN, END

Key mapping
-----------
- ``USAF``       — 6-character WMO station code.  For synoptic land stations
                   the convention is ``zero_padded_5digit_wmo_id + "0"``
                   (e.g. WMO 60402 → USAF "604020").
- ``wmo_id``     — Derived as ``USAF[:5]``.  African blocks are 60 000–69 999.
- ``LAT``/``LON``— Decimal degrees, may carry a leading "+" sign.
- ``CTRY``       — FIPS 10-4 two-letter country code; mapped to ISO 3166-1
                   alpha-3 via ``FIPS_TO_ISO3``.

African WMO blocks
------------------
WMO assigns geographical sub-areas to numeric block ranges.  Africa is
covered by blocks 60–69 (i.e. ``wmo_id`` in range ``"60000"``–``"69999"``).
This is used as the primary continent filter so no country-code mapping is
needed for the basic Africa-only import.

Usage
-----
.. code-block:: python

    from stations.services.isd_station_importer import ISDStationImporter

    result = ISDStationImporter().run(africa_only=True, dry_run=False)
    print(result.created, result.updated, result.skipped)
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Generator

import requests
from django.contrib.gis.geos import Point

from stations.models import Station

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ISD_CSV_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"

# WMO block range that covers Africa and surrounding islands.
AFRICA_WMO_BLOCK_MIN = 60000
AFRICA_WMO_BLOCK_MAX = 69999

# FIPS 10-4 → ISO 3166-1 alpha-3 for African nations.
# Only countries present in the ISD dataset need to be listed.
FIPS_TO_ISO3: dict[str, str] = {
    "AG": "DZA", "AO": "AGO", "BN": "BEN", "BC": "BWA", "UV": "BFA",
    "BY": "BDI", "CV": "CPV", "CM": "CMR", "CT": "CAF", "CD": "TCD",
    "CN": "COM", "CG": "COD", "CF": "COG", "IV": "CIV", "DJ": "DJI",
    "EG": "EGY", "EK": "GNQ", "ER": "ERI", "WZ": "SWZ", "ET": "ETH",
    "GB": "GAB", "GA": "GMB", "GH": "GHA", "GV": "GIN", "PU": "GNB",
    "KE": "KEN", "LT": "LSO", "LI": "LBR", "LY": "LBY", "MA": "MDG",
    "MI": "MWI", "ML": "MLI", "MR": "MRT", "MP": "MUS", "MO": "MAR",
    "MZ": "MOZ", "WA": "NAM", "NG": "NER", "NI": "NGA", "RW": "RWA",
    "TP": "STP", "SG": "SEN", "SE": "SYC", "SL": "SLE", "SO": "SOM",
    "SF": "ZAF", "OD": "SSD", "SU": "SDN", "TZ": "TZA", "TO": "TGO",
    "TS": "TUN", "UG": "UGA", "ZA": "ZMB", "ZI": "ZWE",
    "RE": "REU", "MF": "MYT",  # Réunion / Mayotte (FR overseas)
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ISDRow:
    """Parsed, validated row ready for database upsert."""
    usaf: str
    wmo_id: str          # 5-digit WMO block+station number
    name: str
    country_code: str | None   # ISO 3166-1 alpha-3
    latitude: float
    longitude: float
    elevation_m: float | None


@dataclass
class ImportResult:
    """Summary returned by :meth:`ISDStationImporter.run`."""
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    messages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------

class ISDStationImporter:
    """Fetch the NOAA ISD station history CSV and upsert :class:`~stations.models.Station` rows."""

    def __init__(self, csv_url: str = ISD_CSV_URL, timeout: int = 60) -> None:
        self.csv_url = csv_url
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, *, africa_only: bool = True, dry_run: bool = False, limit: int | None = None) -> ImportResult:
        """Fetch, parse, and upsert stations.

        Parameters
        ----------
        africa_only:
            When ``True`` (default) only import stations in WMO blocks 60–69.
        dry_run:
            Parse and validate without writing to the database.
        limit:
            Stop after processing this many valid rows (useful for testing).

        Returns
        -------
        :class:`ImportResult`
        """
        result = ImportResult()

        try:
            raw_csv = self._fetch_csv()
        except Exception as exc:
            result.errors += 1
            result.messages.append(f"CSV fetch failed: {exc}")
            return result

        count = 0
        for row in self._parse_rows(raw_csv, africa_only=africa_only):
            if limit is not None and count >= limit:
                break

            if dry_run:
                result.created += 1  # count as "would create"
                count += 1
                continue

            action = self._upsert_station(row, result)
            if action != "error":
                count += 1

        return result

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def _fetch_csv(self) -> str:
        """Download the ISD history CSV and return it as a string."""
        log.info("Fetching ISD station history from %s", self.csv_url)
        resp = requests.get(self.csv_url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    def _parse_rows(self, raw_csv: str, *, africa_only: bool) -> Generator[ISDRow, None, None]:
        """Yield validated :class:`ISDRow` objects from the raw CSV text."""
        reader = csv.DictReader(io.StringIO(raw_csv))
        for raw in reader:
            row = self._parse_one(raw)
            if row is None:
                continue
            if africa_only and not self._is_african(row.wmo_id):
                continue
            yield row

    def _parse_one(self, raw: dict[str, str]) -> ISDRow | None:
        """Validate and convert a single CSV row; return ``None`` to skip."""
        usaf = raw.get("USAF", "").strip()

        # Must be a 6-char numeric code (ignores missing/header values)
        if not usaf.isdigit() or len(usaf) != 6:
            return None

        lat_str = raw.get("LAT", "").strip().lstrip("+")
        lon_str = raw.get("LON", "").strip().lstrip("+")
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            return None

        # Skip stations at (0, 0) or with clearly invalid coordinates
        if lat == 0.0 and lon == 0.0:
            return None
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None

        elev_str = raw.get("ELEV(M)", "").strip().lstrip("+")
        try:
            elev = float(elev_str) if elev_str not in ("", "-999.9", "-9999") else None
        except ValueError:
            elev = None

        fips = raw.get("CTRY", "").strip().upper()
        country_code = FIPS_TO_ISO3.get(fips)

        name = (raw.get("STATION NAME") or usaf).strip() or usaf
        wmo_id = usaf[:5]   # Drop the trailing padding digit

        return ISDRow(
            usaf=usaf,
            wmo_id=wmo_id,
            name=name,
            country_code=country_code,
            latitude=lat,
            longitude=lon,
            elevation_m=elev,
        )

    @staticmethod
    def _is_african(wmo_id: str) -> bool:
        """Return ``True`` if the 5-digit WMO ID falls in the African block range (60000–69999)."""
        try:
            return AFRICA_WMO_BLOCK_MIN <= int(wmo_id) <= AFRICA_WMO_BLOCK_MAX
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def _upsert_station(self, row: ISDRow, result: ImportResult) -> str:
        """Insert or update a single station; increment *result* counters in place."""
        try:
            station, created = Station.objects.get_or_create(
                wmo_id=row.wmo_id,
                defaults=self._station_defaults(row),
            )

            if created:
                result.created += 1
                return "created"

            # Update any missing fields on the existing record
            changed = self._apply_updates(station, row)
            if changed:
                result.updated += 1
                return "updated"

            result.skipped += 1
            return "skipped"

        except Exception as exc:
            log.exception("Failed to upsert station wmo_id=%s", row.wmo_id)
            result.errors += 1
            result.messages.append(f"wmo_id={row.wmo_id}: {exc}")
            return "error"

    @staticmethod
    def _station_defaults(row: ISDRow) -> dict:
        return {
            "station_code": row.wmo_id,
            "name": row.name,
            "country_code": row.country_code,
            "geom": Point(row.longitude, row.latitude, srid=4326),
            "elevation_m": row.elevation_m,
            "station_type": Station.StationType.SYNOP,
            "is_active": True,
        }

    @staticmethod
    def _apply_updates(station: Station, row: ISDRow) -> bool:
        """Fill in any blank fields; return ``True`` if a save was needed."""
        changed = False
        if not station.name or station.name == station.station_code:
            station.name = row.name
            changed = True
        if not station.country_code and row.country_code:
            station.country_code = row.country_code
            changed = True
        if station.elevation_m is None and row.elevation_m is not None:
            station.elevation_m = row.elevation_m
            changed = True
        if changed:
            station.save(update_fields=["name", "country_code", "elevation_m", "updated_at"])
        return changed
