"""Pure string-pattern rendering for THREDDS folder/filename/item-id templates.

No I/O here - str.format against a date/int context. date.__format__ already
delegates a non-empty format spec to strftime, so "{run_date:%Y%m%d}" needs no
custom code.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


class PatternRenderError(ValueError):
    pass


def _context(*, run_date: date, lead_hours: int | None, threshold_label: str, dataset_id: str) -> dict:
    ctx: dict = {
        "run_date": run_date,
        "dataset_id": dataset_id,
        # Always present, unlike lead_hours/threshold below: valid_date is
        # well-defined from run_date alone (defaults to run_date itself when
        # there's no lead dimension), for products whose filename embeds a
        # second *date* rather than a bare hour count, e.g.
        # heat_index_{run_date:%Y%m%d}_{valid_date:%Y%m%d}.tif.
        "valid_date": render_valid_datetime(run_date, lead_hours).date(),
    }
    # Omit lead_hours/threshold entirely when unset (lead_hours is None, not
    # merely falsy - 0 is a legitimate configured lead, e.g. a "day 0"
    # forecast in a 0/24/48h series), so a pattern referencing {lead_hours}
    # on a mapping with none configured raises loudly instead of silently
    # rendering "...None.tif".
    if lead_hours is not None:
        ctx["lead_hours"] = lead_hours
    if threshold_label:
        ctx["threshold"] = threshold_label
    return ctx


def render(
    pattern: str,
    *,
    run_date: date,
    lead_hours: int | None = None,
    threshold_label: str = "",
    dataset_id: str = "",
) -> str:
    ctx = _context(
        run_date=run_date, lead_hours=lead_hours, threshold_label=threshold_label, dataset_id=dataset_id
    )
    try:
        return pattern.format(**ctx)
    except KeyError as exc:
        raise PatternRenderError(f"pattern {pattern!r} references missing key {exc}") from exc


def render_source_url(
    workflow,
    workflow_file,
    run_date: date,
    lead_hours: int | None = None,
) -> tuple[str, str]:
    """Return (source_url, filename)."""
    base = workflow.source_base_url.rstrip("/")
    folder = render(workflow.folder_pattern, run_date=run_date)
    filename = render(
        workflow_file.filename_pattern,
        run_date=run_date,
        lead_hours=lead_hours,
        threshold_label=workflow_file.threshold_label,
    )
    return f"{base}/{folder}/{filename}", filename


def render_item_id(
    workflow_file,
    dataset_id: str,
    run_date: date,
    lead_hours: int | None = None,
) -> str:
    if workflow_file.item_id_pattern:
        return render(
            workflow_file.item_id_pattern,
            run_date=run_date,
            lead_hours=lead_hours,
            threshold_label=workflow_file.threshold_label,
            dataset_id=dataset_id,
        )
    if lead_hours is not None:
        return f"{dataset_id}_{run_date:%Y%m%d}_{lead_hours}h"
    return f"{dataset_id}_{run_date:%Y%m%d}"


def render_valid_datetime(run_date: date, lead_hours: int | None = None) -> datetime:
    base = datetime(run_date.year, run_date.month, run_date.day, tzinfo=timezone.utc)
    return base + timedelta(hours=lead_hours or 0)
