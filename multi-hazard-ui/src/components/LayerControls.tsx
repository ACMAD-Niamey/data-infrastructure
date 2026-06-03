import { useState } from 'react';
import Select from 'react-select';
import { Info } from 'lucide-react';
import { Language } from '../types';
import { Card } from './ui/card';
import type {
  CatalogLayer,
  LayerSelectOption,
  LayerSelectionValue,
  SelectorConfig,
  SelectorKey,
} from '../types/catalogLayer';
import '../styles/layercontrol.css';

interface LayerControlsProps {
  layers: CatalogLayer[];
  activeLayerId: string | null;
  onLayerChange: (layerId: string) => void;
  language: Language;
  selectionValues: Record<string, LayerSelectionValue>;
  selectionOptions: Record<string, Partial<Record<SelectorKey, LayerSelectOption[]>>>;
  onSelectionChange: (layerId: string, field: SelectorKey, value?: string) => void;
  loading?: boolean;
  error?: string | null;
}

const translations = {
  en: {
    title: 'Data Layers',
    loading: 'Loading layers…',
    empty: 'No layers published for this project.',
    error: 'Could not load layers',
  },
  fr: {
    title: 'Couches de Données',
    loading: 'Chargement des couches…',
    empty: 'Aucune couche publiée pour ce projet.',
    error: 'Impossible de charger les couches',
  },
};

export function LayerControls({
  layers,
  activeLayerId,
  onLayerChange,
  language,
  selectionValues,
  selectionOptions,
  onSelectionChange,
  loading,
  error,
}: LayerControlsProps) {
  const t = translations[language];
  const [infoLayerId, setInfoLayerId] = useState<string | null>(null);

  const isFieldEnabled = (selection: LayerSelectionValue, field: SelectorConfig) => {
    if (!field.dependsOn || field.dependsOn.length === 0) {
      return true;
    }
    return field.dependsOn.every((dependency) => Boolean(selection[dependency]));
  };

  if (loading) {
    return (
      <div className="p-4 border-b">
        <h2 className="mb-3">{t.title}</h2>
        <p className="text-sm text-gray-500">{t.loading}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border-b">
        <h2 className="mb-3">{t.title}</h2>
        <p className="text-sm text-red-600">{t.error}</p>
      </div>
    );
  }

  if (!layers.length) {
    return (
      <div className="p-4 border-b">
        <h2 className="mb-3">{t.title}</h2>
        <p className="text-sm text-gray-500">{t.empty}</p>
      </div>
    );
  }

  return (
    <div className="p-4 border-b">
      <h2 className="mb-3">{t.title}</h2>
      <div className="space-y-2">
        {layers.map((layer) => {
          const isActive = activeLayerId === layer.id;
          const colorClass = layer.ui?.color_class || 'text-blue-600';
          const description = layer.description?.plain || layer.labels.description[language];

          return (
            <div key={layer.id} className="space-y-2">
              <Card
                className={`p-3 cursor-pointer transition-all ${
                  isActive
                    ? 'bg-green-50 border-green-500 shadow-md'
                    : 'hover:bg-gray-50 border-gray-200'
                }`}
                onClick={() => onLayerChange(layer.id)}
              >
                <div className="flex items-start gap-3">
                  {layer.icon?.url ? (
                    <img
                      src={layer.icon.url}
                      alt={layer.title}
                      className="size-8 mt-0.5 object-contain shrink-0"
                    />
                  ) : null}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className={isActive ? 'text-green-900 font-medium' : ''}>
                        {layer.labels.title[language]}
                      </span>
                      {description ? (
                        <button
                          type="button"
                          className={`shrink-0 p-0.5 rounded hover:bg-gray-200 ${colorClass}`}
                          aria-label={language === 'fr' ? 'Informations' : 'Info'}
                          onClick={(event) => {
                            event.stopPropagation();
                            setInfoLayerId((current) =>
                              current === layer.id ? null : layer.id,
                            );
                          }}
                        >
                          <Info className="size-4" />
                        </button>
                      ) : null}
                    </div>
                    {infoLayerId === layer.id && description ? (
                      <p className="text-xs text-gray-600 mt-1 border-l-2 border-gray-300 pl-2">
                        {description}
                      </p>
                    ) : null}
                  </div>
                </div>
              </Card>

              {isActive && layer.selectors.length > 0 ? (
                <div className="pl-8 pr-1 pb-1" onClick={(event) => event.stopPropagation()}>
                  <div className="flex flex-wrap items-end gap-2">
                    {layer.selectors.map((field) => {
                      const selection = selectionValues[layer.id] || {};
                      const options = selectionOptions[layer.id]?.[field.key] || [];
                      const selectedOption =
                        options.find((option) => option.value === selection[field.key]) ||
                        null;
                      const enabled = isFieldEnabled(selection, field);

                      return (
                        <div
                          key={`${layer.id}-${field.key}`}
                          className="flex-1"
                          style={{ minWidth: field.minWidthPx || 120 }}
                        >
                          <p className="mb-1 text-xs text-gray-600">
                            {field.label[language]}
                          </p>
                          <Select
                            className="layer-select"
                            classNamePrefix="layer-select-controls"
                            options={options}
                            value={selectedOption}
                            isClearable={!field.required}
                            isDisabled={!enabled}
                            placeholder={language === 'fr' ? 'Sélectionner..' : 'Select..'}
                            onChange={(option) =>
                              onSelectionChange(layer.id, field.key, option?.value)
                            }
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
