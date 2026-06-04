from fastmcp import FastMCP
from client import api_get


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_hazard_categories() -> list[dict]:
        """List all hazard categories (drought, flood, climate, etc.) with their keys."""
        return await api_get("/api/catalog/hazard-categories/")

    @mcp.tool()
    async def list_catalog_layers(project: str) -> list[dict]:
        """List published map layers for a project (e.g. 'multi-hazard', 'e-safari').
        Returns layer id, title, cadence, and hazard category."""
        data = await api_get("/api/catalog/ui/layers", project=project)
        return [
            {
                "id":              l.get("id"),
                "title":           l.get("title"),
                "cadence":         l.get("dataset", {}).get("cadence"),
                "hazard_category": l.get("hazard_category"),
                "default_visible": l.get("ui", {}).get("default_visible"),
            }
            for l in data.get("layers", [])
        ]

    @mcp.tool()
    async def get_dataset_availability(dataset_id: str, cadence: str = "daily") -> dict:
        """Get available dates for a dataset. cadence: daily | dekadal | monthly | static."""
        return await api_get(
            f"/api/catalog/datasets/{dataset_id}/availability/",
            cadence=cadence,
        )

    @mcp.tool()
    async def get_dataset_visualization(dataset_id: str, date: str, cadence: str) -> dict:
        """Get the tile URL for a dataset on a specific date.
        date: YYYY-MM-DD or YYYY-MM. cadence: daily | dekadal | monthly | static."""
        return await api_get(
            f"/api/catalog/datasets/{dataset_id}/visualization/",
            date=date,
            cadence=cadence,
        )
