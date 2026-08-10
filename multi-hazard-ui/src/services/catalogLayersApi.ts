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

export async function fetchProjectLayers(
  projectSlug: string,
  options: { requireIcon?: boolean } = {},
): Promise<CatalogLayer[]> {
  const { requireIcon = true } = options;
  const response = await client.get<UILayersResponse>("/api/catalog/ui/layers", {
    params: { project: projectSlug },
  });
  const layers = response.data.layers || [];
  return (requireIcon ? layers.filter((layer) => layer.icon?.url) : layers).map(enrichLayer);
}

export function getProjectSlug(): string {
  const viteEnv = import.meta.env as { VITE_PROJECT_SLUG?: string };
  return (viteEnv.VITE_PROJECT_SLUG || "multi-hazard").trim();
}

export type ProjectConfig = {
  data_platforms_title: string;
  data_platforms_description: string;
  data_platforms_image_url: string | null;
};

/** Project-level config (CMS-editable copy/images). Only the Data Platforms
 * fields are typed here — the endpoint also returns e-safari-ui-specific
 * fields (about/partners/feedback) that this app doesn't use. */
export async function fetchProjectConfig(projectSlug: string): Promise<ProjectConfig> {
  const response = await client.get<ProjectConfig>(`/api/catalog/projects/${projectSlug}/config/`);
  return response.data;
}
