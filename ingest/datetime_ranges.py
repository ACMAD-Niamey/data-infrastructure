"""Cadence-aware datetime intervals for STAC item lookup (ingest/delete)."""

from __future__ import annotations

from datetime import datetime


def _parse_iso(value: str) -> datetime:
    s = (value or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def month_range(year: int, month: int) -> tuple[str, str]:
    start = f"{year:04d}-{month:02d}-01T00:00:00Z"
    next_month = 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year
    end = f"{next_year:04d}-{next_month:02d}-01T00:00:00Z"
    return start, end


def day_range(year: int, month: int, day: int) -> tuple[str, str]:
    start = f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z"
    end = f"{year:04d}-{month:02d}-{day:02d}T23:59:59Z"
    return start, end


def interval_from_payload(cadence: str, payload: dict) -> tuple[str, str]:
    """
    Return STAC datetime interval ``start/end`` for delete lookup.

    ``payload`` uses the same fields as ingest (datetime or start/end).
    """
    if cadence in ("dekadal", "seasonal"):
        start_dt = payload.get("start_datetime")
        end_dt = payload.get("end_datetime")
        if not start_dt or not end_dt:
            raise ValueError("start_datetime and end_datetime are required")
        start = _parse_iso(str(start_dt)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = _parse_iso(str(end_dt)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return start, end

    dt_raw = payload.get("datetime")
    if not dt_raw:
        raise ValueError("datetime is required")

    dt = _parse_iso(str(dt_raw))
    year, month, day = dt.year, dt.month, dt.day

    if cadence == "daily":
        return day_range(year, month, day)
    if cadence == "monthly":
        return month_range(year, month)

    # dekadal without start/end: treat as month window from datetime
    return month_range(year, month)
