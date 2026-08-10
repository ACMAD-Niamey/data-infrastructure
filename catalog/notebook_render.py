"""Render a dataset's example Jupyter notebook to standalone HTML, with Redis caching."""

from __future__ import annotations

from django.core.cache import cache

from .models import Layer

CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 7 days; keyed on file_hash so a re-upload busts it naturally


def render_dataset_notebook_html(dataset_id: str) -> str | None:
    """Return cached/rendered full HTML document for a dataset's example notebook, or None."""
    layer = (
        Layer.objects
        .filter(
            dataset__dataset_id=dataset_id,
            dataset__live=True,
            dataset__is_published_for_ui=True,
            example_notebook__isnull=False,
        )
        .select_related("example_notebook", "dataset")
        .first()
    )
    if not layer:
        return None

    doc = layer.example_notebook
    cache_key = f"catalog:notebook_html:{doc.id}:{doc.get_file_hash()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    html = _export_notebook_html(doc)
    cache.set(cache_key, html, timeout=CACHE_TIMEOUT)
    return html


def _export_notebook_html(doc) -> str:
    import nbformat
    from nbconvert import HTMLExporter

    with doc.file.open("rb") as f:
        nb = nbformat.read(f, as_version=4)

    # Full standalone document (not the "basic" fragment template) - the frontend
    # embeds this in an <iframe srcDoc>, a separate document context with no CSS
    # of its own, so we need nbconvert's own embedded styling/highlighting.
    #
    # sanitize_html stays at its nbconvert default (False): turning it on strips
    # the <script>-based rich outputs (Plotly/Bokeh/Altair) that make inline
    # rendering worth doing over a static image dump. The iframe sandbox on the
    # frontend (allow-scripts, no allow-same-origin) is the real security
    # boundary here, not nbconvert's sanitizer - appropriate since notebooks are
    # curated uploads by trusted Wagtail staff, not arbitrary end-user content.
    exporter = HTMLExporter(template_name="lab")
    body, _resources = exporter.from_notebook_node(nb)
    return body
