import { Language } from '../types';
import { Card } from './ui/card';
import { DataLayer, layerRegistry } from './layers/layerRegistry';

interface LayerControlsProps {
  activeLayer: DataLayer;
  onLayerChange: (layer: DataLayer) => void;
  language: Language;
}

const translations = {
  en: {
    title: 'Data Layers',
  },
  fr: {
    title: 'Couches de Données',
  }
};

export function LayerControls({ activeLayer, onLayerChange, language }: LayerControlsProps) {
  const t = translations[language];

  return (
    <div className="p-4 border-b">
      <h2 className="mb-3">{t.title}</h2>
      <div className="space-y-2">
        {layerRegistry.map((layer) => {
          const Icon = layer.icon;
          return (
            <Card
              key={layer.id}
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
          );
        })}
      </div>
    </div>
  );
}
