import { Thermometer, Trees, Satellite, Brain, MapPin, type LucideIcon } from "lucide-react";
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

export type LayerConfig = {
  id: "heat" | "green-cover" | "satellite" | "modeled" | "point-data";
  icon: LucideIcon;
  color: string;
  label: LayerLabel;
  description: LayerLabel;
  renderAnalysis: (args: LayerAnalysisArgs) => JSX.Element;
};

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
    renderAnalysis: ({ language }) => <PointDataStatistics language={language} />,
  },
];

export type DataLayer = LayerConfig["id"];
