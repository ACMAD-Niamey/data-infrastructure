from fastmcp import FastMCP
from client import api_get


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_latest_observations(
        country_code: str | None = None,
        variable_code: str | None = None,
    ) -> list[dict]:
        """Get the most recent observations per station/variable.
        country_code: ISO 3166-1 alpha-3. variable_code: temp | rainfall | rh | etc."""
        return await api_get(
            "/api/observations/latest/",
            country_code=country_code,
            variable_code=variable_code,
        )

    @mcp.tool()
    async def get_observation_stats(
        variable_code: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Get aggregated statistics for a variable across all stations over a date range.
        start_date/end_date: YYYY-MM-DD."""
        return await api_get(
            "/api/observations/stats/",
            variable_code=variable_code,
            start=start_date,
            end=end_date,
        )
