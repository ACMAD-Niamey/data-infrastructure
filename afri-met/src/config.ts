/**
 * Shared host root used to build service paths.
 *
 * `VITE_API_BASE_URL` should be host-only (example: `http://localhost`).
 * For backward compatibility, a trailing `/api` in env is stripped.
 */
export function getHostBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!raw) return "http://localhost";
  return raw.replace(/\/$/, "").replace(/\/api$/, "");
}

/** Django REST root. */
export function getApiBaseUrl(): string {
  return `${getHostBaseUrl()}/api`;
}

/** TiPG root proxied by nginx. */
export function getTipgBaseUrl(): string {
  return `${getHostBaseUrl()}/tipg`;
}
