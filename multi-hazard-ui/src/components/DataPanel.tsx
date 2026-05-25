import { Language } from '../types';
import { SelectedFeatureStats } from './stats/SelectedFeatureStats';
import { SelectedFeature } from '../Portal';
import type { CatalogLayer } from '../types/catalogLayer';
import { renderLegend } from './LegendUtils';

interface DataPanelProps {
  activeLayer: CatalogLayer | null;
  language: Language;
  selectedFeature?: SelectedFeature | null;
}

const emptyCopy = {
  en: 'Select a layer to view its legend and description.',
  fr: 'Sélectionnez une couche pour voir sa légende et sa description.',
};

export function DataPanel({ activeLayer, language, selectedFeature }: DataPanelProps) {
  return (
    <div className="p-4 space-y-4">
      {selectedFeature && (
        <SelectedFeatureStats
          feature={selectedFeature}
          language={language}
          onClose={() => {}}
        />
      )}

      {!activeLayer ? (
        <p className="text-sm text-gray-500">{emptyCopy[language]}</p>
      ) : (
        <>
          {activeLayer.description?.plain ? (
            <p className="text-sm text-gray-700">{activeLayer.description.plain}</p>
          ) : null}
          {activeLayer.legend && Object.keys(activeLayer.legend).length > 0
            ? renderLegend(activeLayer.legend, activeLayer.title)
            : null}
        </>
      )}
    </div>
  );
}
