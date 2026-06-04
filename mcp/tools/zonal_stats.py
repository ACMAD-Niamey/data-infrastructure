from __future__ import annotations
import json
from fastmcp import FastMCP
from client import api_get, stac_post, titiler_post
import cache as _cache


def _extract_href(item: dict) -> str | None:
    assets = item.get("assets", {})
    for key in ("data", "cog", "visual"):
        if key in assets:
            return assets[key].get("href")
    for asset in assets.values():
        href = asset.get("href")
        if href:
            return href
    return None


def _parse_stats(titiler_response: dict) -> dict:
    features = titiler_response.get("features", [])
    if not features:
        return {}
    stats = features[0].get("properties", {}).get("statistics", {})
    # take first band (b1 for single-band rasters)
    band = next(iter(stats.values()), {}) if stats else {}
    return {
        "mean":  round(band.get("mean", 0), 4),
        "min":   round(band.get("min", 0), 4),
        "max":   round(band.get("max", 0), 4),
        "std":   round(band.get("std", 0), 4),
        "p2":    round(band.get("percentile_2", 0), 4),
        "p98":   round(band.get("percentile_98", 0), 4),
    }


async def _country_geojson(country_code: str) -> dict:
    """Fetch full country GeoJSON polygon from Django. Falls back to bbox Feature if not found."""
    try:
        return await api_get(f"/api/stations/country-boundary/{country_code}/")
    except Exception:
        # fallback: construct a bbox polygon from country-bounds
        raw = await api_get("/api/stations/country-bounds/")
        match = next((c for c in raw if c["value"].upper() == country_code.upper()), None)
        if not match:
            raise ValueError(f"Country '{country_code}' not found.")
        b = match["bounds"]
        return {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [b["west"], b["south"]], [b["east"], b["south"]],
                    [b["east"], b["north"]], [b["west"], b["north"]],
                    [b["west"], b["south"]],
                ]],
            },
        }


async def _compute_stats(href: str, country_feature: dict) -> dict:
    fc = {"type": "FeatureCollection", "features": [country_feature]}
    resp = await titiler_post("/cog/statistics", params={"url": href}, geojson_body=fc)
    return _parse_stats(resp)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_country_raster_stats(
        country_code: str,
        dataset_id: str,
        date: str,
    ) -> dict:
        """Compute zonal statistics for a country over a raster dataset on a specific date.
        country_code: ISO alpha-3 (use resolve_country() first if you have a name).
        dataset_id: STAC collection id (e.g. 'spi', 'ndvi').
        date: YYYY-MM-DD.
        Returns {date, mean, min, max, std, p2, p98}."""
        cache_key = f"zonal:{dataset_id}:{country_code.upper()}:{date}"
        cached = await _cache.get(cache_key)
        if cached:
            return cached

        country_feature = await _country_geojson(country_code)
        bounds = country_feature.get("bbox") or [
            country_feature["geometry"]["coordinates"][0][0][0],
            country_feature["geometry"]["coordinates"][0][0][1],
            country_feature["geometry"]["coordinates"][0][2][0],
            country_feature["geometry"]["coordinates"][0][2][1],
        ]

        # find the STAC item for this date
        stac_result = await stac_post("/search", {
            "collections": [dataset_id],
            "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z",
            "limit": 1,
        })
        items = stac_result.get("features", [])
        if not items:
            raise ValueError(f"No STAC item found for dataset '{dataset_id}' on {date}.")

        href = _extract_href(items[0])
        if not href:
            raise ValueError(f"STAC item for '{dataset_id}' on {date} has no asset href.")

        stats = await _compute_stats(href, country_feature)
        result = {"date": date, **stats}
        await _cache.set(cache_key, result)
        return result

    @mcp.tool()
    async def get_country_raster_timeseries(
        country_code: str,
        dataset_id: str,
        start_date: str,
        end_date: str,
        limit: int = 12,
        force_refresh: bool = False,
    ) -> list[dict]:
        """Compute zonal statistics for a country over a raster dataset across a date range.
        Returns a time series [{date, mean, min, max, std, p2, p98}, ...] sorted ascending.
        limit: max items to process (default 12, max 36).
        force_refresh: bypass Redis cache."""
        limit = min(limit, 36)
        country_feature = await _country_geojson(country_code)

        stac_result = await stac_post("/search", {
            "collections": [dataset_id],
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "limit": limit,
            "sortby": [{"field": "datetime", "direction": "asc"}],
        })
        items = stac_result.get("features", [])
        if not items:
            raise ValueError(
                f"No STAC items found for '{dataset_id}' between {start_date} and {end_date}."
            )

        results = []
        for item in items:
            date_str = (
                item.get("properties", {}).get("datetime")
                or item.get("properties", {}).get("start_datetime", "")
            )[:10]

            cache_key = f"zonal:{dataset_id}:{country_code.upper()}:{date_str}"
            if not force_refresh:
                cached = await _cache.get(cache_key)
                if cached:
                    results.append(cached)
                    continue

            href = _extract_href(item)
            if not href:
                continue

            stats = await _compute_stats(href, country_feature)
            entry = {"date": date_str, **stats}
            await _cache.set(cache_key, entry)
            results.append(entry)

        return sorted(results, key=lambda x: x["date"])
