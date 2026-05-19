import type { LayerSelectOption, LayerSelectionValue, SelectorKey } from "../types/catalogLayer";
import { catalogBaseUrl, layersApiBaseUrl } from "../config/api";
import axios from "axios";

type FetchSelectorOptionsParams = {
  layerId: string;
  field: SelectorKey;
  selection?: LayerSelectionValue;
};

type SelectorOptionsApiResponse = {
  options: LayerSelectOption[];
};

type SatelliteAvailabilityResponse = {
  dataset_id: string;
  cadence: string;
  available: string[];
  min?: string;
  max?: string;
};

type SatelliteVisualizationResponse = {
  dataset_id: string;
  cadence: string;
  titiler_url?: string[];
  titiler_info?: {
    tiles?: string[];
    bounds?: [number, number, number, number];
  };
};

export type BoundsObject = {
  minx: number;
  miny: number;
  maxx: number;
  maxy: number;
};

export type SatelliteAvailabilityResult = {
  options: LayerSelectOption[];
  max: string | null;
  min: string | null;
};

export type SatelliteVisualizationResult = {
  tileUrl: string | null;
  bounds: BoundsObject | null;
};


const catalogClient = axios.create({
  baseURL: catalogBaseUrl,
  timeout: 15000,
});

const months = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  fr: ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"],
};

export const getFallbackSelectorOptions = (field: SelectorKey, language: "en" | "fr"): LayerSelectOption[] => {
  const currentYear = new Date().getFullYear();

  switch (field) {
    case "year":
      return Array.from({ length: 11 }, (_, index) => {
        const year = String(currentYear - index);
        return { value: year, label: year };
      });
    case "month":
      return months[language].map((month, index) => ({ value: String(index + 1), label: month }));
    case "date":
      return Array.from({ length: 31 }, (_, index) => {
        const day = String(index + 1);
        return { value: day, label: day };
      });
    case "dekad":
      return [
        { value: "1", label: language === "fr" ? "Décade 1" : "Dekad 1" },
        { value: "2", label: language === "fr" ? "Décade 2" : "Dekad 2" },
        { value: "3", label: language === "fr" ? "Décade 3" : "Dekad 3" },
      ];
    case "season":
      return ["DJF", "MAM", "JJA", "SON"].map((season) => ({ value: season, label: season }));
    default:
      return [];
  }
};

export const fetchSelectorOptions = async ({
  layerId,
  field,
  selection,
}: FetchSelectorOptionsParams): Promise<LayerSelectOption[]> => {
  if (!layersApiBaseUrl) {
    return [];
  }

  const query = new URLSearchParams();
  query.set("field", field);

  Object.entries(selection || {}).forEach(([key, value]) => {
    if (!value) return;
    query.set(key, value);
  });

  const endpoint = `${layersApiBaseUrl}/layers/${layerId}/options?${query.toString()}`;
  const response = await fetch(endpoint);

  if (!response.ok) {
    throw new Error(`Failed to fetch selector options: ${response.status}`);
  }

  const payload = (await response.json()) as SelectorOptionsApiResponse | LayerSelectOption[];
  if (Array.isArray(payload)) {
    return payload;
  }

  return payload.options || [];
};

const toBoundsObject = (bounds?: [number, number, number, number]): BoundsObject | null => {
  if (!bounds || bounds.length !== 4) {
    return null;
  }

  const [minx, miny, maxx, maxy] = bounds;
  return { minx, miny, maxx, maxy };
};

export const fetchDatasetAvailability = async ({
  datasetId,
  cadence = "monthly",
}: {
  datasetId: string;
  cadence?: string;
}): Promise<SatelliteAvailabilityResult> => {
  const response = await catalogClient.get<SatelliteAvailabilityResponse>(
    `/api/catalog/datasets/${datasetId}/availability/`,
    { params: { cadence } },
  );

  const payload = response.data;
  const available = payload.available || [];
  const options = available
    .slice()
    .sort((left, right) => right.localeCompare(left))
    .map((value) => ({ value, label: value }));

  return {
    options,
    max: payload.max || null,
    min: payload.min || null,
  };
};

export const fetchDatasetVisualization = async ({
  datasetId,
  cadence = "monthly",
  date,
}: {
  datasetId: string;
  cadence?: string;
  date: string;
}): Promise<SatelliteVisualizationResult> => {
  const response = await catalogClient.get<SatelliteVisualizationResponse>(
    `/api/catalog/datasets/${datasetId}/visualization/`,
    { params: { cadence, date } },
  );

  const payload = response.data;
  const tileUrl = payload.titiler_url?.[0] || payload.titiler_info?.tiles?.[0] || null;

  return {
    tileUrl,
    bounds: toBoundsObject(payload.titiler_info?.bounds),
  };
};

/** @deprecated Use fetchDatasetAvailability */
export const fetchSatelliteAvailability = fetchDatasetAvailability;

/** @deprecated Use fetchDatasetVisualization */
export const fetchSatelliteVisualization = fetchDatasetVisualization;
