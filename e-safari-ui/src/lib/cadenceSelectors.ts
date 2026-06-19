import type { Language } from "../types";
import type { LayerSelectionValue, SelectorConfig, SelectorKey } from "../types/catalogLayer";

const labels = {
  year: { en: "Year", fr: "Année" },
  month: { en: "Month", fr: "Mois" },
  date: { en: "Date", fr: "Date" },
  dekad: { en: "Dekad", fr: "Décade" },
  season: { en: "Season", fr: "Saison" },
};

export function deriveSelectors(cadence: string, language: Language): SelectorConfig[] {
  const L = (key: keyof typeof labels) => ({
    ...labels[key],
    en: labels[key].en,
    fr: labels[key].fr,
  });

  switch (cadence) {
    case "daily":
      return [
        { key: "year", label: L("year"), required: true, minWidthPx: 110 },
        { key: "month", label: L("month"), dependsOn: ["year"], minWidthPx: 130 },
        { key: "date", label: L("date"), dependsOn: ["year", "month"], minWidthPx: 100 },
      ];
    case "dekadal":
      return [
        { key: "year", label: L("year"), required: true, minWidthPx: 110 },
        { key: "month", label: L("month"), dependsOn: ["year"], minWidthPx: 130 },
        { key: "dekad", label: L("dekad"), dependsOn: ["year", "month"], minWidthPx: 120 },
      ];
    case "seasonal":
      return [
        { key: "year", label: L("year"), required: true, minWidthPx: 110 },
        { key: "season", label: L("season"), dependsOn: ["year"], minWidthPx: 140 },
      ];
    case "annual":
      return [{ key: "year", label: L("year"), required: true, minWidthPx: 110 }];
    case "monthly":
    default:
      return [{ key: "date", label: L("date"), required: true, minWidthPx: 170 }];
  }
}

/** Build API `date` query value from layer selection and cadence. */
export function buildVisualizationDate(
  cadence: string,
  selection: LayerSelectionValue,
): string | null {
  const { date, year, month, dekad, season } = selection;

  if (date && /^\d{4}-\d{2}(-\d{2})?$/.test(date)) {
    return date;
  }

  if (!year) {
    return null;
  }

  const y = year;
  const m = month ? String(month).padStart(2, "0") : null;

  switch (cadence) {
    case "monthly":
      return m ? `${y}-${m}` : null;
    case "daily": {
      if (!m || !selection.date) {
        return null;
      }
      const day = String(selection.date).padStart(2, "0");
      return `${y}-${m}-${day}`;
    }
    case "dekadal": {
      if (!m || !dekad) {
        return null;
      }
      const dekadDay = { "1": "01", "2": "11", "3": "21" }[dekad] ?? "01";
      return `${y}-${m}-${dekadDay}`;
    }
    case "seasonal":
      return season ? `${y}-${season}` : null;
    case "annual":
      return y;
    default:
      return date ?? null;
  }
}

