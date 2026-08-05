# Documentation

Project documentation for **GeoDataManager** (geomgr) and its consumer applications.

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | Current system: services, data flow, frontends (e-safari-ui, Afri-Met), and how they connect to PostGIS and TiPG. |
| [Ingest and delete API](ingest-delete.md) | STAC raster ingest (`POST`) and delete by item id or datetime (catalog-only vs STAC + MinIO). |
| [THREDDS download & ingestion](thredds-ingestion.md) | Automated daily GeoTIFF pull from ACMAD THREDDS into existing datasets/styles: workflow config, idempotency, backfill, and scheduling. |
| [e-safari dynamic layers](e-safari-layers.md) | Wagtail layer icons, datasets, and UI catalog API for e-safari-ui. |
| [Roadmap](roadmap.md) | Planned evolution: multi-hazard surfaces, central UI, MCP-assisted maps and statistics, LLM chatbot. |

For setup and operations, see the repository [README](../README.md).
