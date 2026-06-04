from fastmcp import FastMCP
from client import stac_get, stac_post


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_stac_collections() -> list[dict]:
        """List all STAC collections (ingested raster datasets) with title, description, and spatial/temporal extent."""
        data = await stac_get("/collections")
        return [
            {
                "id":          c.get("id"),
                "title":       c.get("title"),
                "description": c.get("description"),
                "extent":      c.get("extent"),
            }
            for c in data.get("collections", [])
        ]

    @mcp.tool()
    async def get_stac_collection(collection_id: str) -> dict:
        """Get metadata for a single STAC collection including its full spatial and temporal extent."""
        return await stac_get(f"/collections/{collection_id}")

    @mcp.tool()
    async def search_stac_items(
        collection_id: str | None = None,
        bbox: list[float] | None = None,
        datetime_range: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Search STAC items (raster dataset records).
        datetime_range: ISO 8601 instant or interval e.g. '2026-01-01T00:00:00Z/2026-06-01T00:00:00Z'.
        bbox: [west, south, east, north].
        Returns items with their datetime, bbox, and asset hrefs."""
        body: dict = {"limit": min(limit, 100)}
        if collection_id:
            body["collections"] = [collection_id]
        if bbox:
            body["bbox"] = bbox
        if datetime_range:
            body["datetime"] = datetime_range
        data = await stac_post("/search", body)
        return {
            "matched": data.get("context", {}).get("matched"),
            "items": [
                {
                    "id":       item.get("id"),
                    "datetime": item.get("properties", {}).get("datetime")
                                or item.get("properties", {}).get("start_datetime"),
                    "bbox":     item.get("bbox"),
                    "assets":   {k: v.get("href") for k, v in item.get("assets", {}).items()},
                }
                for item in data.get("features", [])
            ],
        }
