from fastmcp import FastMCP
from client import api_get


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def search_stations(
        country_code: str | None = None,
        admin1: str | None = None,
        has_observations: bool | None = None,
    ) -> dict:
        """Search weather stations. country_code is ISO 3166-1 alpha-3 (e.g. ETH, KEN).
        Use resolve_country() first if you only have a country name.
        Returns station list and spatial extent."""
        params: dict = {}
        if country_code:
            params["country_code"] = country_code.upper()
        if admin1:
            params["admin1"] = admin1
        return await api_get("/api/stations/", **params)

    @mcp.tool()
    async def get_station_detail(station_code: str) -> dict:
        """Get full metadata for a single station including sensors and variable coverage."""
        return await api_get(f"/api/stations/{station_code}/")

    @mcp.tool()
    async def get_station_stats(
        station_code: str,
        variable: str,
        start: str,
        end: str,
        agg: str = "daily",
    ) -> dict:
        """Get time-series statistics for a variable at a station.
        variable: temp | rainfall | rh | pressure | wind_speed | wind_direction | dewpoint.
        agg: raw | hourly | daily | monthly | yearly.
        start/end: YYYY-MM-DD."""
        return await api_get(
            f"/api/stations/{station_code}/stats/",
            variable=variable,
            start=start,
            end=end,
            agg=agg,
        )

    @mcp.tool()
    async def get_station_facets(country_code: str | None = None) -> dict:
        """Get distinct countries and admin1 regions that have stations with observations.
        Useful for understanding data coverage before querying."""
        return await api_get("/api/stations/facets/", country_code=country_code)
