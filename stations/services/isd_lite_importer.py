"""NOAA ISD-Lite hourly historical observation importer.

Source format
-------------
Plain ASCII, one UTC-hour per line, whitespace-separated::

    year mo dy hr  temp dewp  slp  wdir wspd skyc prcp_1h prcp_6h

``-9999`` denotes missing. ``-1`` in ``prcp_*`` denotes trace precipitation.
Most numeric fields are scaled by 10.

URL pattern::

    https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/<year>/<USAF>-<WBAN>-<year>.gz

Idempotency
-----------
The ``observations`` primary key is ``(station_id, variable_code, observed_at)``,
so we rely on ``bulk_create(ignore_conflicts=True)`` to make re-runs no-ops.
"""

from __future__ import annotations

import csv
import gzip
import io
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

import requests

from observations.models import Observation
from sources.models import DataSource, Dataset, Policy
from stations.models import Station

log = logging.getLogger(__name__)


ISD_LITE_BASE = "https://www.ncei.noaa.gov/pub/data/noaa/isd-lite"
ISD_HISTORY_CSV_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
DEFAULT_WBAN = "99999"
QC_FLAG = "noaa_isd_lite"

# Column index in the parsed line -> (variable_code, unit, divisor).
# Indices reflect whitespace-split rows: [year, mo, dy, hr, temp, dewp, slp,
# wdir, wspd, skyc, prcp_1h, prcp_6h].
VARIABLE_MAP: dict[int, tuple[str, str, float]] = {
    4: ("temp", "degC", 10.0),
    6: ("pressure", "hPa", 10.0),
    7: ("wind_direction", "deg", 1.0),
    8: ("wind_speed", "m/s", 10.0),
    10: ("rainfall", "mm", 10.0),
}

_MISSING = -9999
_TRACE = -1


@dataclass
class ImportResult:
    station_code: str
    year: int
    archive_url: str | None = None
    parsed: int = 0
    written: int = 0
    skipped_existing: int = 0
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def parse_lines(text: str) -> Iterable[tuple[datetime, str, float, str]]:
    """Yield ``(observed_at, variable_code, value, unit)`` from raw ISD-Lite text.

    Pure: no I/O, no DB. Missing values (``-9999``) are dropped. Trace precip
    (``-1`` in any ``prcp_*`` column) is normalized to ``0.0``.
    """
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 11:
            continue
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            hour = int(parts[3])
        except ValueError:
            continue

        try:
            observed_at = datetime(year, month, day, hour, tzinfo=timezone.utc)
        except ValueError:
            continue

        for idx, (code, unit, divisor) in VARIABLE_MAP.items():
            if idx >= len(parts):
                continue
            try:
                raw = int(parts[idx])
            except ValueError:
                continue
            if raw == _MISSING:
                continue
            if code == "rainfall" and raw == _TRACE:
                value = 0.0
            else:
                value = raw / divisor
            yield observed_at, code, float(value), unit


class ISDLiteImporter:
    """Fetch and import NOAA ISD-Lite hourly archives.

    The instance caches the optional WBAN history map so a single CLI/Celery
    invocation only fetches the ~7 MB CSV once, and only when needed.
    """

    def __init__(self, *, timeout: int = 60) -> None:
        self.timeout = timeout
        self._wban_map: dict[str, list[str]] | None = None

    # ---- public API --------------------------------------------------------

    def import_year(
        self,
        *,
        station: Station,
        year: int,
        dry_run: bool = False,
    ) -> ImportResult:
        result = ImportResult(station_code=station.station_code, year=year)
        usaf = self._usaf_for(station)
        if not usaf:
            result.error = "missing USAF"
            return result

        text, archive_url = self._fetch_archive(usaf, year)
        result.archive_url = archive_url
        if text is None:
            result.error = "archive not found"
            return result

        source, dataset = self._ensure_source_and_dataset()

        records: list[Observation] = []
        ingest_time = datetime.now(timezone.utc)
        for observed_at, code, value, unit in parse_lines(text):
            result.parsed += 1
            records.append(
                Observation(
                    station=station,
                    sensor=None,
                    dataset=dataset,
                    source=source,
                    observed_at=observed_at,
                    variable_code=code,
                    raw_value=value,
                    cleaned_value=value,
                    unit=unit,
                    qc_flag=QC_FLAG,
                    ingest_time=ingest_time,
                    payload_ref=archive_url,
                )
            )

        if dry_run or not records:
            return result

        attempted = len(records)
        cohort = self._cohort_qs(station=station, year=year)
        existing_before = cohort.count()
        Observation.objects.bulk_create(
            records, batch_size=2000, ignore_conflicts=True,
        )
        existing_after = cohort.count()
        result.written = max(existing_after - existing_before, 0)
        result.skipped_existing = max(attempted - result.written, 0)
        return result

    @staticmethod
    def _cohort_qs(*, station: Station, year: int):
        year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
        year_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        return Observation.objects.filter(
            station=station,
            qc_flag=QC_FLAG,
            observed_at__gte=year_start,
            observed_at__lt=year_end,
        )

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _usaf_for(station: Station) -> str | None:
        """Resolve the 6-digit USAF code from station metadata.

        Stations imported by ``import_wmo_stations`` use a 5-digit
        ``station_code = wmo_id`` (the trailing padding digit was dropped).
        ISD-Lite filenames need the full 6-digit USAF, so we right-pad with ``0``.
        """
        code = (station.station_code or "").strip()
        if not code:
            return None
        if len(code) == 6 and code.isdigit():
            return code
        if len(code) == 5 and code.isdigit():
            return code + "0"
        return None

    def _fetch_archive(self, usaf: str, year: int) -> tuple[str | None, str | None]:
        for wban in self._wban_candidates(usaf):
            url = f"{ISD_LITE_BASE}/{year}/{usaf}-{wban}-{year}.gz"
            try:
                response = requests.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                log.warning("ISD-Lite fetch failed for %s: %s", url, exc)
                continue
            if response.status_code == 404:
                continue
            response.raise_for_status()
            try:
                text = gzip.decompress(response.content).decode("ascii", errors="replace")
            except OSError as exc:
                log.warning("ISD-Lite gunzip failed for %s: %s", url, exc)
                continue
            return text, url
        return None, None

    def _wban_candidates(self, usaf: str) -> list[str]:
        candidates = [DEFAULT_WBAN]
        for wban in self._wban_map_for(usaf):
            if wban not in candidates:
                candidates.append(wban)
        return candidates

    def _wban_map_for(self, usaf: str) -> list[str]:
        if self._wban_map is None:
            self._wban_map = self._load_wban_map()
        return self._wban_map.get(usaf, [])

    def _load_wban_map(self) -> dict[str, list[str]]:
        try:
            response = requests.get(ISD_HISTORY_CSV_URL, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            log.warning("ISD history CSV fetch failed: %s", exc)
            return {}
        reader = csv.DictReader(io.StringIO(response.text))
        out: dict[str, list[str]] = {}
        for raw in reader:
            usaf = (raw.get("USAF") or "").strip()
            wban = (raw.get("WBAN") or "").strip()
            if not usaf or not wban:
                continue
            out.setdefault(usaf, []).append(wban)
        return out

    @staticmethod
    def _ensure_source_and_dataset() -> tuple[DataSource, Dataset]:
        source, _ = DataSource.objects.get_or_create(
            source_code="noaa_isd_lite",
            defaults={
                "source_name": "NOAA ISD-Lite",
                "source_type": DataSource.SourceType.NOAA,
                "protocol": DataSource.ProtocolType.HTTPS,
                "endpoint_url": ISD_LITE_BASE,
                "is_active": True,
            },
        )
        policy, _ = Policy.objects.get_or_create(
            name="Internal Only",
            defaults={
                "owner_org": "Internal",
                "public_api_allowed": False,
                "dashboard_allowed": False,
                "internal_allowed": True,
                "partner_allowed": False,
                "raw_download_allowed": False,
                "aggregate_allowed": True,
                "station_visible": True,
            },
        )
        dataset, _ = Dataset.objects.get_or_create(
            dataset_code="noaa_isd_lite_hourly",
            defaults={
                "source": source,
                "policy": policy,
                "dataset_name": "ISD-Lite Hourly",
                "variable_family": "surface_observations",
                "temporal_resolution": "hourly",
                "is_active": True,
            },
        )
        return source, dataset
