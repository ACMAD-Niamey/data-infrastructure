"""Which value flavours (raw / cleaned) a station's series may expose.

Both are always stored; the owning DatasetPage decides what is public. The
check lives server-side so a client cannot request a hidden series by editing
the query string.
"""

from __future__ import annotations

from catalog.models import DatasetPage
from stations.models import Station

RAW = "raw"
CLEANED = "cleaned"
# value query param -> observations column
VALUE_COLUMNS = {RAW: "raw_value", CLEANED: "cleaned_value"}


def allowed_values(station_code: str) -> list[str]:
    """Stations without a controlling DatasetPage (WIS2, NOAA...) predate this
    feature and keep their historical behaviour: raw only."""
    meta = (
        Station.objects.filter(station_code=station_code)
        .values_list("metadata_json", flat=True)
        .first()
    ) or {}
    dataset_code = meta.get("dataset_code")
    page = DatasetPage.objects.filter(dataset_id=dataset_code).first() if dataset_code else None
    if page is None:
        return [RAW]

    allowed = []
    if page.show_raw_values:
        allowed.append(RAW)
    if page.show_cleaned_values:
        allowed.append(CLEANED)
    return allowed
