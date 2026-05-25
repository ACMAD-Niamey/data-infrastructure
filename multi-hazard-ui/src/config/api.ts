/** Production catalog/API origin (paths include `/api/catalog/...`). */
export const DEFAULT_BASE_URL = "https://multi-hazard.acmad.org";

/**
 * Normalize BASE_URL from .env: trim slashes and strip trailing `/api`
 * so `http://localhost/api` and `http://localhost` both work.
 */
export function normalizeApiBaseUrl(raw: string | undefined): string {
  let url = (raw || "").trim();
  if (!url) {
    return DEFAULT_BASE_URL;
  }
  url = url.replace(/\/+$/, "");
  if (url.endsWith("/api")) {
    url = url.slice(0, -4);
  }
  return url || DEFAULT_BASE_URL;
}

const viteEnv = import.meta.env as {
  VITE_BASE_URL?: string;
  VITE_CATALOG_API_BASE_URL?: string;
  VITE_LAYERS_API_BASE_URL?: string;
};

/** Catalog + dataset visualization API origin. */
export const catalogBaseUrl = normalizeApiBaseUrl(
  viteEnv.VITE_BASE_URL || viteEnv.VITE_CATALOG_API_BASE_URL,
);

/** Optional separate layers selector API; empty disables remote options fetch. */
export const layersApiBaseUrl = (viteEnv.VITE_LAYERS_API_BASE_URL || "").replace(/\/+$/, "");
