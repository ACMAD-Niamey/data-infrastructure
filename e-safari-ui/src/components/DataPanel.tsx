import { Language } from '../types';
import { SelectedFeatureStats } from './stats/SelectedFeatureStats';
import { SelectedFeature } from '../Portal';
import { DataLayer, layerRegistry } from './layers/layerRegistry';

interface DataPanelProps {
  activeLayer: DataLayer;
  language: Language;
  selectedFeature?: SelectedFeature | null;
  selectedYear?: string;
  onYearChange?: (year: string) => void;
}

export function DataPanel({ activeLayer, language, selectedFeature, selectedYear, onYearChange }: DataPanelProps) {
  const activeConfig = layerRegistry.find((layer) => layer.id === activeLayer);

  return (
    <div className="p-4 space-y-4">
      {selectedFeature && (
        <SelectedFeatureStats 
          feature={selectedFeature} 
          language={language}
          onClose={() => {}}
        />
      )}
      
      {activeConfig?.renderAnalysis({ language, selectedYear, onYearChange })}
    </div>
  );
}