import { catalogBaseUrl } from "../config/api";

export const base_url_ada = "https://ada.acmad.org";

  export const maplibre_str =
  "bbox={bbox-epsg-3857}&format=image/png&service=WMS&version=1.1.1&request=GetMap&srs=EPSG:3857&width=256&height=256&layers=";

  /** API origin (catalog, TiTiler via backend); from BASE_URL in .env, default production. */
  export const base_url = catalogBaseUrl;


