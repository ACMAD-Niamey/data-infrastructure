"""Calendar-month arithmetic shared by the scheduler and the backfill command.

Monthly- and seasonal-cadence workflows key their runs by a 1st-of-month
``run_date`` (the seasonal anchor month for a season), so both the Celery Beat
task and ``run_download_workflow`` need to step and enumerate by whole months
rather than by days. ``datetime``/``timedelta`` have no month unit, hence this
tiny module - no I/O, pure date math.
"""

from __future__ import annotations

import calendar
from datetime import date


def clamp_day(year: int, month: int, day: int) -> date:
    """``date(year, month, day)`` with ``day`` capped at that month's real
    length, so a configured day-of-month like 31 lands on the 28th/29th/30th
    where the month is shorter rather than raising or silently shifting to a
    fixed 28."""
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def add_months(anchor: date, delta: int) -> date:
    """Return the 1st of the month ``delta`` calendar months from ``anchor``.

    ``delta`` may be negative. The day component of ``anchor`` is discarded -
    the result is always day 1, which is the canonical run_date for a
    monthly/seasonal period.
    """
    month_index = anchor.year * 12 + (anchor.month - 1) + delta
    return date(month_index // 12, month_index % 12 + 1, 1)


def month_range(start: date, end: date) -> list[date]:
    """Inclusive list of 1st-of-month dates from ``start`` to ``end``.

    Both bounds are normalised to day 1 first, so ``month_range(2025-01-15,
    2025-03-02)`` yields Jan/Feb/Mar 1st.
    """
    cursor = start.replace(day=1)
    stop = end.replace(day=1)
    out: list[date] = []
    while cursor <= stop:
        out.append(cursor)
        cursor = add_months(cursor, 1)
    return out
