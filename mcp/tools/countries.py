from fastmcp import FastMCP
from client import api_get


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_countries() -> list[dict]:
        """List all countries that have boundary data, with their canonical codes and bounding boxes.
        Use this to discover which countries are available before running statistics."""
        raw = await api_get("/api/stations/country-bounds/")
        return [
            {"code": c["value"], "label": c["label"], "bounds": c["bounds"]}
            for c in raw
        ]

    @mcp.tool()
    async def resolve_country(name_or_code: str) -> dict:
        """Resolve a country name or partial name to its canonical ISO alpha-3 code and bounds.
        Example: 'Ethiopia' → {code: 'ETH', label: 'Ethiopia', bounds: {west, south, east, north}}.
        The returned 'code' is what all other tools expect for country_code parameters."""
        raw = await api_get("/api/stations/country-bounds/")
        query = name_or_code.strip().upper()

        # exact code match first
        for c in raw:
            if c["value"].upper() == query:
                return {"code": c["value"], "label": c["label"], "bounds": c["bounds"]}

        # case-insensitive label match (partial)
        query_lower = name_or_code.strip().lower()
        matches = [c for c in raw if query_lower in c["label"].lower()]
        if not matches:
            available = [c["label"] for c in raw]
            raise ValueError(
                f"No country matching '{name_or_code}'. Available: {available}"
            )
        c = matches[0]
        return {"code": c["value"], "label": c["label"], "bounds": c["bounds"]}
