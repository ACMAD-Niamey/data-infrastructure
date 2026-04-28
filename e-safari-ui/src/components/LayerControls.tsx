import Select from 'react-select';
import { Language } from '../types';
import { Card } from './ui/card';
import { DataLayer, layerRegistry, LayerSelectOption, LayerSelectionValue, SelectorConfig, SelectorKey } from './layers/layerRegistry';
// import {add_image_layer, remove_image_layer} from './Maputils';
// import { useMap } from "./MapContext.jsx"
import '../styles/layercontrol.css';

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
//    const { mapRef } = useMap() ?? { mapRef: { current: null } };

  const isFieldEnabled = (selection: LayerSelectionValue, field: SelectorConfig) => {
    if (!field.dependsOn || field.dependsOn.length === 0) {
      return true;
    }
    return field.dependsOn.every((dependency) => Boolean(selection[dependency]));
  };

//   const boundsArray = [
//   37.87998010486817,
//   -0.25144460148935915,
//   37.89064998256544,
//   -0.24131712218419182
// ];

// const [minx, miny, maxx, maxy] = boundsArray;

// const bounds = { minx, miny, maxx, maxy };

// var dataset_url = "https://climatehub.acmad.org/titiler/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=https%3A%2F%2Fminio.acmad.org%2Fgeodata%2FTharaka_Nithi_Mission_2_transparent_mosaic_RGB.tif&bidx=1&bidx=2&bidx=3&tilesize=512"

//     // add_image_layer(mapRef.current, dataset_url, "test-layer", true, bounds, true);

    // 
  
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
                            className='layer-select'
                            classNamePrefix="layer-select-controls"
                            options={options}
                            value={selectedOption}
                            isClearable={!field.required}
                            isDisabled={!enabled}
                            placeholder={language === 'fr' ? 'Sélectionner..' : 'Select..'}
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
