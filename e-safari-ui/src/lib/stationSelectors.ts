import type { Language } from "../types";
import type {
  CatalogLayer,
  LayerSelectOption,
  SelectorConfig,
  SelectorKey,
} from "../types/catalogLayer";

/** Variables the heat-campaign loggers record, in display order. */
export const STATION_VARIABLES = [
  { value: "temp", unit: "°C", en: "Air temperature", fr: "Température de l'air" },
  { value: "globe_temp", unit: "°C", en: "Globe temperature", fr: "Température globe noir" },
  { value: "rh", unit: "%", en: "Relative humidity", fr: "Humidité relative" },
  { value: "lux", unit: "lx", en: "Illuminance", fr: "Éclairement" },
  { value: "battery_v", unit: "V", en: "Battery", fr: "Batterie" },
] as const;

const AGGREGATIONS = [
  { value: "hourly", en: "Hourly", fr: "Horaire" },
  { value: "daily", en: "Daily", fr: "Journalier" },
  { value: "raw", en: "Raw (1 min, last 3 days)", fr: "Brut (1 min, 3 derniers jours)" },
] as const;

const VALUES = [
  { value: "raw", en: "Raw", fr: "Brut" },
  { value: "cleaned", en: "Cleaned", fr: "Nettoyé" },
] as const;

/** Same shape as the raster date selectors so LayerControls renders them unchanged. */
export function stationSelectors(): SelectorConfig[] {
  return [
    { key: "variable", label: { en: "Variable", fr: "Variable" }, required: true, minWidthPx: 150 },
    { key: "agg", label: { en: "Aggregation", fr: "Agrégation" }, required: true, minWidthPx: 130 },
    { key: "value", label: { en: "Values", fr: "Valeurs" }, required: true, minWidthPx: 100 },
  ];
}

/**
 * Options are static, except `value`, which mirrors what the dataset page
 * publishes. The API enforces the same flags, so this only hides choices that
 * would be rejected.
 */
export function stationSelectorOptions(
  layer: CatalogLayer,
  language: Language,
): Partial<Record<SelectorKey, LayerSelectOption[]>> {
  const cfg = layer.station_timeseries;
  const pick = <T extends { value: string; en: string; fr: string }>(items: readonly T[]) =>
    items.map((i) => ({ value: i.value, label: i[language] }));

  return {
    variable: pick(STATION_VARIABLES),
    agg: pick(AGGREGATIONS),
    value: pick(VALUES).filter(
      (o) => (o.value === "raw" ? cfg?.show_raw_values ?? true : cfg?.show_cleaned_values ?? false),
    ),
  };
}

export function variableMeta(code: string) {
  return STATION_VARIABLES.find((v) => v.value === code);
}
