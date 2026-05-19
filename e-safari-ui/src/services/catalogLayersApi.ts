import axios from "axios";
import { catalogBaseUrl } from "../config/api";
import { deriveSelectors } from "../lib/cadenceSelectors";
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
  const cadence = raw.dataset.cadence;
  return {
    ...raw,
    selectors: deriveSelectors(cadence, "en"),
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
