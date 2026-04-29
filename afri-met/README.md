# Afri-Met

React + MapLibre UI for exploring ACMAD GeoDataManager **stations** and **observation time series**.

## Prerequisites

- Django API reachable with `/api/stations/` (same repo `manage.py runserver`, typically port **8000**).
- Applied migrations including **`stations.0003_stations_mvt_tile_view`** (PostGIS view `tiles.stations_mvt` for optional TiPG vector tiles).

## Run (development)

From repo root:

```bash
cd geomgr
python manage.py runserver   # http://127.0.0.1:8000
```

Second terminal:

```bash
cd geomgr/afri-met
npm install
npm run dev                  # http://127.0.0.1:5174 — proxies /api → Django
```

The Vite dev server proxies **`/api`** to **`http://127.0.0.1:8000`** by default. Override with:

```bash
VITE_PROXY_TARGET=http://localhost:8070 npm run dev
```

(if your Django listens on another host/port).

### API URL (`VITE_API_BASE_URL`)

Copy `.env.example` to `.env` or `.env.local` if you need to override the API root.

| Scenario | Typical value |
|----------|----------------|
| **Vite dev** (no `.env`) | Defaults to **`/api`** so requests hit the dev proxy (same-origin). |
| **Production build** (no `.env`) | Defaults to **`http://localhost/api`** — matches nginx forwarding `/api` to Django when the browser loads the SPA from `http://localhost`. |
| **Explicit override** | `VITE_API_BASE_URL=http://localhost/api` or `VITE_API_BASE_URL=/api` |

Only variables prefixed with `VITE_` are exposed to the client bundle.

### Mapbox basemaps (`VITE_MAPBOX_KEY`)

Same pattern as **e-safari-ui**: set **`VITE_MAPBOX_KEY`** in `.env` to your Mapbox **public** token. The map uses an empty style plus **`BasemapsControl`** (satellite / light / streets). Without a token, Afri-Met falls back to **MapLibre demo tiles** (no basemap picker).

## Features (v1)

- Map with stations loaded as **GeoJSON** from `GET /api/stations/` (filters supported).
- **Extent** from the API drives **`fitBounds`** after filtering by country / admin regions.
- **Facets** from `GET /api/stations/facets/` populate dropdowns.
- Tap or click a station → panel with variable / aggregation / date range and **Recharts** line chart from `GET /api/stations/<code>/stats/`.
- **Mobile**: bottom sheet–style panel + backdrop; desktop: fixed-width sidebar.

## Optional: TiPG vector tiles

After Tipg discovers `tiles.stations_mvt`, you can point MapLibre at Tipg MVT URLs (future enhancement). GeoJSON mode remains the default for simplicity in development.
