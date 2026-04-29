/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Host base URL, e.g. `http://localhost` (API and TiPG paths are derived). */
  readonly VITE_API_BASE_URL?: string;
  /** Mapbox public token for raster basemaps (same as e-safari-ui). Optional: falls back to demo tiles. */
  readonly VITE_MAPBOX_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
