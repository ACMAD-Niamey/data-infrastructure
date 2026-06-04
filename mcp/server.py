import os
from fastmcp import FastMCP
from tools import catalog, stac, stations, observations, countries, zonal_stats

mcp = FastMCP("GeoOracle")

catalog.register(mcp)
stac.register(mcp)
stations.register(mcp)
observations.register(mcp)
countries.register(mcp)
zonal_stats.register(mcp)

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(
            transport="sse",
            host="0.0.0.0",
            port=int(os.getenv("MCP_PORT", "8090")),
        )
    else:
        mcp.run()
