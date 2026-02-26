import { Thermometer, Trees, Satellite, Brain, MapPin, type LucideIcon } from "lucide-react";
import type { ReactElement } from "react";
import { HeatStatistics } from "../stats/HeatStatistics";
import { GreenCoverStatistics } from "../stats/GreenCoverStatistics";
import { SatelliteStatistics } from "../stats/SatelliteStatistics";
import { ModeledStatistics } from "../stats/ModeledStatistics";
import { PointDataStatistics } from "../stats/PointDataStatistics";
import { Language } from "../../types";

type LayerLabel = {
  en: string;
  fr: string;
};

type LayerAnalysisArgs = {
  language: Language;
  selectedYear?: string;
  onYearChange?: (year: string) => void;
};

export type SelectorKey = "year" | "month" | "date" | "dekad" | "season";

export type LayerSelectOption = {
  value: string;
  label: string;
};

export type SelectorConfig = {
  key: SelectorKey;
  label: LayerLabel;
  required?: boolean;
  dependsOn?: SelectorKey[];
  minWidthPx?: number;
};

export type LayerSelectionConfig = {
  selectors?: SelectorConfig[];
};

export type LayerConfig = {
  id: "heat" | "green-cover" | "satellite" | "modeled" | "point-data";
  icon: LucideIcon;
  color: string;
  label: LayerLabel;
  description: LayerLabel;
  selection?: LayerSelectionConfig;
  renderAnalysis: (args: LayerAnalysisArgs) => ReactElement;
};

export type LayerSelectionValue = Partial<Record<SelectorKey, string>>;

export const layerRegistry: LayerConfig[] = [
  {
    id: "heat",
    icon: Thermometer,
    color: "text-red-600",
    label: { en: "Heat Map", fr: "Carte de Chaleur" },
    description: {
      en: "Surface temperature distribution",
      fr: "Distribution de température de surface",
    },
    selection: {
      selectors: [
        { key: "year", label: { en: "Year", fr: "Année" }, required: true, minWidthPx: 110 },
        { key: "month", label: { en: "Month", fr: "Mois" }, dependsOn: ["year"], minWidthPx: 130 },
        { key: "date", label: { en: "Date", fr: "Date" }, dependsOn: ["year", "month"], minWidthPx: 100 },
      ],
    },
    renderAnalysis: ({ language }) => <HeatStatistics language={language} />,
  },
  {
    id: "green-cover",
    icon: Trees,
    color: "text-green-600",
    label: { en: "Green Cover", fr: "Couverture Verte" },
    description: {
      en: "Vegetation and tree canopy",
      fr: "Végétation et canopée",
    },
    selection: {
      selectors: [
        { key: "year", label: { en: "Year", fr: "Année" }, required: true, minWidthPx: 110 },
        { key: "season", label: { en: "Season", fr: "Saison" }, dependsOn: ["year"], minWidthPx: 140 },
      ],
    },
    renderAnalysis: ({ language }) => <GreenCoverStatistics language={language} />,
  },
  {
    id: "satellite",
    icon: Satellite,
    color: "text-blue-600",
    label: { en: "Satellite Data", fr: "Données Satellite" },
    description: {
      en: "Remote sensing imagery",
      fr: "Imagerie de télédétection",
    },
    selection: {
      selectors: [
        { key: "date", label: { en: "Date", fr: "Date" }, required: true, minWidthPx: 170 },
      ],
    },
    renderAnalysis: ({ language }) => <SatelliteStatistics language={language} />,
  },
  {
    id: "modeled",
    icon: Brain,
    color: "text-purple-600",
    label: { en: "Modeled Data", fr: "Données Modélisées" },
    description: {
      en: "Climate predictions",
      fr: "Prévisions climatiques",
    },
    selection: {
      selectors: [
        { key: "year", label: { en: "Year", fr: "Année" }, required: true, minWidthPx: 110 },
        { key: "season", label: { en: "Season", fr: "Saison" }, dependsOn: ["year"], minWidthPx: 140 },
      ],
    },
    renderAnalysis: ({ language, selectedYear, onYearChange }) => (
      <ModeledStatistics
        language={language}
        selectedYear={selectedYear || "2024"}
        onYearChange={onYearChange || (() => {})}
      />
    ),
  },
  {
    id: "point-data",
    icon: MapPin,
    color: "text-orange-600",
    label: { en: "Field Measurements", fr: "Mesures de Terrain" },
    description: {
      en: "Sun vs shade readings",
      fr: "Lectures soleil vs ombre",
    },
    selection: {
      selectors: [
        { key: "year", label: { en: "Year", fr: "Année" }, required: true, minWidthPx: 110 },
      ],
    },
    renderAnalysis: ({ language }) => <PointDataStatistics language={language} />,
  },
];

export type DataLayer = LayerConfig["id"];
