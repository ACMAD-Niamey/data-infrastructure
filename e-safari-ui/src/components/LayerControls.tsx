import Select from 'react-select';
import { Language } from '../types';
import { Card } from './ui/card';
import { DataLayer, layerRegistry, LayerSelectOption, LayerSelectionValue, SelectorConfig, SelectorKey } from './layers/layerRegistry';

interface LayerControlsProps {
  activeLayer: DataLayer;
  onLayerChange: (layer: DataLayer) => void;
  language: Language;
  selectionValues: Record<DataLayer, LayerSelectionValue>;
  selectionOptions: Record<DataLayer, Partial<Record<SelectorKey, LayerSelectOption[]>>>;
  onSelectionChange: (layer: DataLayer, field: SelectorKey, value?: string) => void;
}

const translations = {
  en: {
    title: 'Data Layers',
  },
  fr: {
    title: 'Couches de Données',
  }
};

export function LayerControls({ activeLayer, onLayerChange, language, selectionValues, selectionOptions, onSelectionChange }: LayerControlsProps) {
  const t = translations[language];

  const isFieldEnabled = (selection: LayerSelectionValue, field: SelectorConfig) => {
    if (!field.dependsOn || field.dependsOn.length === 0) {
      return true;
    }
    return field.dependsOn.every((dependency) => Boolean(selection[dependency]));
  };

  return (
    <div className="p-4 border-b">
      <h2 className="mb-3">{t.title}</h2>
      <div className="space-y-2">
        {layerRegistry.map((layer) => {
          const Icon = layer.icon;
          return (
            <div key={layer.id} className="space-y-2">
              <Card
                className={`p-3 cursor-pointer transition-all ${
                  activeLayer === layer.id
                    ? 'bg-green-50 border-green-500 shadow-md'
                    : 'hover:bg-gray-50 border-gray-200'
                }`}
                onClick={() => onLayerChange(layer.id)}
              >
                <div className="flex items-start gap-3">
                  <Icon className={`size-5 mt-0.5 ${layer.color}`} />
                  <div className="flex-1">
                    <div className={activeLayer === layer.id ? 'text-green-900' : ''}>
                      {layer.label[language]}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {layer.description[language]}
                    </p>
                  </div>
                </div>
              </Card>

              {activeLayer === layer.id && layer.selection?.selectors?.length ? (
                <div className="pl-8 pr-1 pb-1" onClick={(event) => event.stopPropagation()}>
                  <div className="flex flex-wrap items-end gap-2">
                    {layer.selection.selectors.map((field) => {
                      const selection = selectionValues[layer.id] || {};
                      const options = selectionOptions[layer.id]?.[field.key] || [];
                      const selectedOption = options.find((option) => option.value === selection[field.key]) || null;
                      const enabled = isFieldEnabled(selection, field);

                      return (
                        <div key={`${layer.id}-${field.key}`} className="flex-1" style={{ minWidth: field.minWidthPx || 120 }}>
                          <p className="mb-1 text-xs text-gray-600">{field.label[language]}</p>
                          <Select
                            classNamePrefix="layer-select"
                            options={options}
                            value={selectedOption}
                            isClearable={!field.required}
                            isDisabled={!enabled}
                            placeholder={language === 'fr' ? 'Sélectionner...' : 'Select...'}
                            onChange={(option) => onSelectionChange(layer.id, field.key, option?.value)}
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
