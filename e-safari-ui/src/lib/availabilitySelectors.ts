import type { LayerSelectOption, LayerSelectionValue, SelectorKey } from "../types/catalogLayer";

const monthLabels = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  fr: ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"],
};

export function optionsFromAvailability(
  available: string[],
  field: SelectorKey,
  selection: LayerSelectionValue,
  language: "en" | "fr" = "en",
): LayerSelectOption[] {
  const sorted = [...available].sort((left, right) => right.localeCompare(left));

  switch (field) {
    case "date":
      return sorted.map((value) => ({ value, label: value }));
    case "year": {
      const years = [...new Set(sorted.map((value) => value.slice(0, 4)))];
      return years.map((value) => ({ value, label: value }));
    }
    case "month": {
      const year = selection.year;
      if (!year) {
        return [];
      }
      const months = [
        ...new Set(
          sorted
            .filter((value) => value.startsWith(`${year}-`))
            .map((value) => value.slice(5, 7)),
        ),
      ];
      return months.map((value) => {
        const index = parseInt(value, 10) - 1;
        const label = monthLabels[language][index] ?? value;
        return { value: String(parseInt(value, 10)), label };
      });
    }
    case "dekad":
      return [
        { value: "1", label: language === "fr" ? "Décade 1" : "Dekad 1" },
        { value: "2", label: language === "fr" ? "Décade 2" : "Dekad 2" },
        { value: "3", label: language === "fr" ? "Décade 3" : "Dekad 3" },
      ];
    case "season":
      return ["DJF", "MAM", "JJA", "SON"].map((value) => ({ value, label: value }));
    default:
      return [];
  }
}

export function defaultSelectionFromAvailability(
  cadence: string,
  available: string[],
  max: string | null,
): LayerSelectionValue {
  const pick = max || available[available.length - 1] || null;
  if (!pick) {
    return {};
  }

  if (cadence === "monthly" || /^\d{4}-\d{2}$/.test(pick)) {
    return { date: pick };
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(pick)) {
    const [year, month, day] = pick.split("-");
    return {
      year,
      month: String(parseInt(month, 10)),
      date: String(parseInt(day, 10)),
    };
  }

  return { date: pick };
}
