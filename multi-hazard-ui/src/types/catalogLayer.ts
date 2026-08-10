import type { Language } from "../types";

export type SelectorKey = "year" | "month" | "date" | "dekad" | "season";

export type LayerLabel = {
  en: string;
  fr: string;
};

export type LayerSelectOption = {
  value: string;
  label: string;
};

export type LayerSelectionValue = Partial<Record<SelectorKey, string>>;

export type SelectorConfig = {
  key: SelectorKey;
  label: LayerLabel;
  required?: boolean;
  dependsOn?: SelectorKey[];
  minWidthPx?: number;
};

export type CatalogDataset = {
  id: string;
  title: string;
  cadence: string;
  dataset_type: string;
  stac_collection: string;
};

export type LayerDetails = {
  coverage: string;
  resolution: string;
  update_frequency: string;
  source_organization: string;
  methodology_html: string;
  methodology_url: string;
  legend_description: string;
  has_notebook: boolean;
  has_stac_collection: boolean;
};

export type CatalogLayer = {
  id: string;
  title: string;
  type: string;
  project: string | null;
  hazard_category?: string;
  details: LayerDetails | null;
  description: {
    html: string;
    plain: string;
  };
  icon: {
    slug: string;
    url: string;
  } | null;
  dataset: CatalogDataset;
  selection: { cadence: string };
  legend: Record<string, string>;
  ui: {
    default_visible: boolean;
    always_on_top: boolean;
    display_on_homepage: boolean;
    opacity: number;
    minzoom: number;
    maxzoom: number;
    color_class: string;
  };
  selectors: SelectorConfig[];
  labels: {
    title: LayerLabel;
    description: LayerLabel;
  };
};

export function catalogLayerLabels(layer: CatalogLayer, language: Language) {
  return {
    title: layer.title,
    description: layer.description.plain,
  };
}
