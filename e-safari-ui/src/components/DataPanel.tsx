import { DataLayer, Language } from '../App';
import { Card } from './ui/card';
import { HeatStatistics } from './stats/HeatStatistics';
import { GreenCoverStatistics } from './stats/GreenCoverStatistics';
import { SatelliteStatistics } from './stats/SatelliteStatistics';
import { ModeledStatistics } from './stats/ModeledStatistics';
import { PointDataStatistics } from './stats/PointDataStatistics';
import { SelectedFeatureStats } from './stats/SelectedFeatureStats';
import { SelectedFeature } from '../App';

interface DataPanelProps {
  activeLayer: DataLayer;
  language: Language;
  selectedFeature?: SelectedFeature | null;
  selectedYear?: string;
  onYearChange?: (year: string) => void;
}

export function DataPanel({ activeLayer, language, selectedFeature, selectedYear, onYearChange }: DataPanelProps) {
  return (
    <div className="p-4 space-y-4">
      {selectedFeature && (
        <SelectedFeatureStats 
          feature={selectedFeature} 
          language={language}
          onClose={() => {}}
        />
      )}
      
      {activeLayer === 'heat' && <HeatStatistics language={language} />}
      {activeLayer === 'green-cover' && <GreenCoverStatistics language={language} />}
      {activeLayer === 'satellite' && <SatelliteStatistics language={language} />}
      {activeLayer === 'modeled' && (
        <ModeledStatistics 
          language={language}
          selectedYear={selectedYear || '2024'}
          onYearChange={onYearChange || (() => {})}
        />
      )}
      {activeLayer === 'point-data' && <PointDataStatistics language={language} />}
    </div>
  );
}