
  # Urban Heat Mitigation Strategy



  ## Running the code

  ## Environment variables

  Create a `.env` file in `e-safari-ui` (copy from `.env.example`):

  - `VITE_MAPBOX_KEY` — Mapbox access token for basemaps
  - `BASE_URL` — API origin for catalog requests (dataset availability, visualization). Default: `https://e-safari.acmad.org`. The app calls paths like `/api/catalog/datasets/...`, so use `http://localhost` for local testing, not a double `/api` path.

  ### Local API testing

  1. Run the geomgr stack (nginx on port 80 serving `/api/...`).
  2. In `e-safari-ui/.env` set `BASE_URL=http://localhost` (or `http://localhost/api`; trailing `/api` is stripped).
  3. `npm run dev` — UI on port 3000. Vite proxies `/api` to `http://localhost` to reduce CORS issues.
  4. For tile URLs in visualization responses to hit local TiTiler, configure geomgr `.env` (`REPLACE_TITILER_URL`, `HTTPS_ENDPOINT_URL`, `TITILER_URL`) separately.

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server.
  