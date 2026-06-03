import { Language, SelectedFeature } from '../../App';
import { Card } from '../ui/card';
import { X, MapPin, Thermometer, Trees, Satellite, Brain } from 'lucide-react';
import { Button } from '../ui/button';

interface SelectedFeatureStatsProps {
  feature: SelectedFeature;
  language: Language;
  onClose: () => void;
}

const translations = {
  en: {
    selectedFeature: 'Selected Feature',
    temperature: 'Temperature',
    sunTemp: 'In Sun',
    shadeTemp: 'In Shade',
    coolingEffect: 'Cooling Effect',
    coverage: 'Green Coverage',
    resolution: 'Resolution',
    projection: 'Projected Temperature (2050)',
    location: 'Location',
    collector: 'Data Collector',
    date: 'Collection Date',
    closeDetails: 'Close Details'
  },
  fr: {
    selectedFeature: 'Élément Sélectionné',
    temperature: 'Température',
    sunTemp: 'Au Soleil',
    shadeTemp: 'À l\'Ombre',
    coolingEffect: 'Effet de Refroidissement',
    coverage: 'Couverture Verte',
    resolution: 'Résolution',
    projection: 'Température Projetée (2050)',
    location: 'Emplacement',
    collector: 'Collecteur de Données',
    date: 'Date de Collecte',
    closeDetails: 'Fermer les Détails'
  }
};

export function SelectedFeatureStats({ feature, language, onClose }: SelectedFeatureStatsProps) {
  const t = translations[language];

  const getIcon = () => {
    switch (feature.type) {
      case 'heat':
        return <Thermometer className="size-5 text-red-600" />;
      case 'green':
        return <Trees className="size-5 text-green-600" />;
      case 'satellite':
        return <Satellite className="size-5 text-blue-600" />;
      case 'modeled':
        return <Brain className="size-5 text-purple-600" />;
      case 'point':
        return <MapPin className="size-5 text-orange-600" />;
      default:
        return <MapPin className="size-5 text-gray-600" />;
    }
  };

  const renderContent = () => {
    if (feature.type === 'heat') {
      return (
        <div className="space-y-2 mt-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">{t.temperature}</span>
            <span className="text-red-600">{feature.data.temp}°C</span>
          </div>
        </div>
      );
    }

    if (feature.type === 'green') {
      return (
        <div className="space-y-2 mt-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">{t.coverage}</span>
            <span className="text-green-600">
              {(feature.data.coverage * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      );
    }

    if (feature.type === 'satellite') {
      return (
        <div className="space-y-2 mt-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">{t.resolution}</span>
            <span className="text-blue-600">{feature.data.resolution}</span>
          </div>
        </div>
      );
    }

    if (feature.type === 'modeled') {
      return (
        <div className="space-y-2 mt-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">{t.projection}</span>
            <span className="text-purple-600">{feature.data.temp2050}°C</span>
          </div>
        </div>
      );
    }

    if (feature.type === 'point') {
      const point = feature.data;
      return (
        <div className="space-y-3 mt-3">
          <div>
            <p className="text-xs text-gray-500 mb-1">{t.location}</p>
            <p>{point.name}</p>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="p-2 bg-orange-50 rounded">
              <p className="text-xs text-gray-600 mb-1">☀ {t.sunTemp}</p>
              <p className="text-orange-600">{point.sunTemp}°C</p>
            </div>
            <div className="p-2 bg-cyan-50 rounded">
              <p className="text-xs text-gray-600 mb-1">🌳 {t.shadeTemp}</p>
              <p className="text-cyan-600">{point.shadeTemp}°C</p>
            </div>
          </div>

          <div className="p-3 bg-green-50 rounded border border-green-200">
            <p className="text-xs text-gray-600 mb-1">{t.coolingEffect}</p>
            <p className="text-green-600">
              -{(point.sunTemp - point.shadeTemp).toFixed(1)}°C
            </p>
          </div>

          <div className="text-xs text-gray-500 space-y-1">
            <p><strong>{t.collector}:</strong> {point.collector}</p>
            <p><strong>{t.date}:</strong> {point.date}</p>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <Card className="p-4 border-2 border-primary bg-primary/5">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {getIcon()}
          <h4>{t.selectedFeature}</h4>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="h-6 w-6 p-0"
        >
          <X className="size-4" />
        </Button>
      </div>
      
      {renderContent()}
    </Card>
  );
}
