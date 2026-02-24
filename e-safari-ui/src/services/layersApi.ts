import { DataLayer, LayerSelectOption, LayerSelectionValue, SelectorKey } from "../components/layers/layerRegistry";

type FetchSelectorOptionsParams = {
  layerId: DataLayer;
  field: SelectorKey;
  selection?: LayerSelectionValue;
};

type SelectorOptionsApiResponse = {
  options: LayerSelectOption[];
};

const apiBaseUrl = import.meta.env.VITE_LAYERS_API_BASE_URL || "";

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
  if (!apiBaseUrl) {
    return [];
  }

  const query = new URLSearchParams();
  query.set("field", field);

  Object.entries(selection || {}).forEach(([key, value]) => {
    if (!value) return;
    query.set(key, value);
  });

  const endpoint = `${apiBaseUrl.replace(/\/$/, "")}/layers/${layerId}/options?${query.toString()}`;
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
