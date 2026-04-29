/**
 * Public API root **including** the `/api` segment (no trailing slash).
 *
 * - **Production default:** `http://localhost/api` — typical nginx → Django prefix.
 * - **Dev (`vite`):** defaults to `/api` so requests stay same-origin and the Vite proxy can forward them.
 *
 * Override with `VITE_API_BASE_URL` in `.env` / `.env.local` / `.env.production`.
 */
export function getApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL?.trim();
  if (raw) {
    return raw.replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    return "/api";
  }
  return "http://localhost/api";
}
