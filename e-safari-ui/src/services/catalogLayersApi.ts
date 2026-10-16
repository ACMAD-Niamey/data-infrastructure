import axios from "axios";
import { catalogBaseUrl } from "../config/api";
import { selectorsForLayer } from "../lib/cadenceSelectors";
import type { CatalogLayer } from "../types/catalogLayer";

export type UILayersResponse = {
  version: string;
  project: string;
  layers: Array<
    Omit<CatalogLayer, "selectors" | "labels"> & {
      description: { html: string; plain: string };
    }
  >;
};

const client = axios.create({
  baseURL: catalogBaseUrl,
  timeout: 15000,
});

function enrichLayer(raw: UILayersResponse["layers"][number]): CatalogLayer {
  // The API's default opacity is a 0-1 fraction, but the UI works in percent. Rasters
  // always carry an explicit percent from their style; station layers have no style, so
  // convert here or their points render at <1% opacity.
  const ui =
    raw.dataset.dataset_type === "station_timeseries" && raw.ui.opacity <= 1
      ? { ...raw.ui, opacity: raw.ui.opacity * 100 }
      : raw.ui;
  return {
    ...raw,
    ui,
    selectors: selectorsForLayer(raw, "en"),
    labels: {
      title: { en: raw.title, fr: raw.title },
      description: { en: raw.description.plain, fr: raw.description.plain },
    },
  };
}

export async function fetchProjectLayers(projectSlug: string): Promise<CatalogLayer[]> {
  const response = await client.get<UILayersResponse>("/api/catalog/ui/layers", {
    params: { project: projectSlug },
  });
  return (response.data.layers || [])
    .filter((layer) => layer.icon?.url)
    .map(enrichLayer);
}

export function getProjectSlug(): string {
  const viteEnv = import.meta.env as { VITE_PROJECT_SLUG?: string };
  return (viteEnv.VITE_PROJECT_SLUG || "e-safari").trim();
}
