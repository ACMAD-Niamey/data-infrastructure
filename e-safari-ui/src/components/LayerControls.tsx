import { DataLayer, Language } from '../App';
import { Thermometer, Trees, Satellite, Brain, MapPin } from 'lucide-react';
import { Card } from './ui/card';

interface LayerControlsProps {
  activeLayer: DataLayer;
  onLayerChange: (layer: DataLayer) => void;
  language: Language;
}

const translations = {
  en: {
    title: 'Data Layers',
    heat: 'Heat Map',
    heatDesc: 'Surface temperature distribution',
    greenCover: 'Green Cover',
    greenCoverDesc: 'Vegetation and tree canopy',
    satellite: 'Satellite Data',
    satelliteDesc: 'Remote sensing imagery',
    modeled: 'Modeled Data',
    modeledDesc: 'Climate predictions',
    pointData: 'Field Measurements',
    pointDataDesc: 'Sun vs shade readings'
  },
  fr: {
    title: 'Couches de Données',
    heat: 'Carte de Chaleur',
    heatDesc: 'Distribution de température de surface',
    greenCover: 'Couverture Verte',
    greenCoverDesc: 'Végétation et canopée',
    satellite: 'Données Satellite',
    satelliteDesc: 'Imagerie de télédétection',
    modeled: 'Données Modélisées',
    modeledDesc: 'Prévisions climatiques',
    pointData: 'Mesures de Terrain',
    pointDataDesc: 'Lectures soleil vs ombre'
  }
};

const layers = [
  { id: 'heat' as DataLayer, icon: Thermometer, color: 'text-red-600' },
  { id: 'green-cover' as DataLayer, icon: Trees, color: 'text-green-600' },
  { id: 'satellite' as DataLayer, icon: Satellite, color: 'text-blue-600' },
  { id: 'modeled' as DataLayer, icon: Brain, color: 'text-purple-600' },
  { id: 'point-data' as DataLayer, icon: MapPin, color: 'text-orange-600' }
];

export function LayerControls({ activeLayer, onLayerChange, language }: LayerControlsProps) {
  const t = translations[language];
  
  const getLayerName = (id: DataLayer) => {
    const key = id.replace('-', '') as keyof typeof t;
    return t[key] || id;
  };
  
  const getLayerDesc = (id: DataLayer) => {
    const key = (id.replace('-', '') + 'Desc') as keyof typeof t;
    return t[key] || '';
  };

  return (
    <div className="p-4 border-b">
      <h2 className="mb-3">{t.title}</h2>
      <div className="space-y-2">
        {layers.map((layer) => {
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
                    {getLayerName(layer.id)}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {getLayerDesc(layer.id)}
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
