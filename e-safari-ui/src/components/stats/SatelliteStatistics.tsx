import { Language } from '../../App';
import { Card } from '../ui/card';
import { Satellite, Calendar, Download, Eye } from 'lucide-react';
import { Button } from '../ui/button';

interface SatelliteStatisticsProps {
  language: Language;
}

const translations = {
  en: {
    title: 'Satellite Data Overview',
    resolution: 'Resolution',
    coverage: 'Area Coverage',
    lastUpdate: 'Last Updated',
    cloudCover: 'Cloud Cover',
    availableImagery: 'Available Imagery',
    landsat: 'Landsat 8/9',
    sentinel: 'Sentinel-2',
    planetScope: 'PlanetScope',
    downloadData: 'Download Data',
    viewSource: 'View Source',
    insights: 'Data Quality',
    insight1: 'High-resolution imagery available for entire city area',
    insight2: 'Multi-spectral analysis enables vegetation health monitoring',
    insight3: 'Bi-weekly updates ensure temporal change detection'
  },
  fr: {
    title: 'Aperçu des Données Satellite',
    resolution: 'Résolution',
    coverage: 'Couverture de Zone',
    lastUpdate: 'Dernière Mise à Jour',
    cloudCover: 'Couverture Nuageuse',
    availableImagery: 'Imagerie Disponible',
    landsat: 'Landsat 8/9',
    sentinel: 'Sentinel-2',
    planetScope: 'PlanetScope',
    downloadData: 'Télécharger Données',
    viewSource: 'Voir Source',
    insights: 'Qualité des Données',
    insight1: 'Imagerie haute résolution disponible pour toute la ville',
    insight2: 'L\'analyse multispectrale permet le suivi de la végétation',
    insight3: 'Mises à jour bihebdomadaires pour détecter les changements'
  }
};

export function SatelliteStatistics({ language }: SatelliteStatisticsProps) {
  const t = translations[language];

  return (
    <div className="space-y-4">
      <div>
        <h3>{t.title}</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Satellite className="size-4 text-blue-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.resolution}</p>
              <p className="text-lg text-blue-600 mt-1">10m</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Eye className="size-4 text-cyan-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.coverage}</p>
              <p className="text-lg text-cyan-600 mt-1">100%</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Calendar className="size-4 text-purple-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.lastUpdate}</p>
              <p className="text-sm text-purple-600 mt-1">Nov 10, 2024</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Satellite className="size-4 text-green-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.cloudCover}</p>
              <p className="text-lg text-green-600 mt-1">8%</p>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <h4 className="mb-3">{t.availableImagery}</h4>
        <div className="space-y-2">
          <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
            <div>
              <p className="text-sm">{t.landsat}</p>
              <p className="text-xs text-gray-500">30m resolution</p>
            </div>
            <Button size="sm" variant="outline">
              <Download className="size-3 mr-1" />
              {language === 'en' ? 'Get' : 'Obtenir'}
            </Button>
          </div>
          
          <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
            <div>
              <p className="text-sm">{t.sentinel}</p>
              <p className="text-xs text-gray-500">10m resolution</p>
            </div>
            <Button size="sm" variant="outline">
              <Download className="size-3 mr-1" />
              {language === 'en' ? 'Get' : 'Obtenir'}
            </Button>
          </div>
          
          <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
            <div>
              <p className="text-sm">{t.planetScope}</p>
              <p className="text-xs text-gray-500">3m resolution</p>
            </div>
            <Button size="sm" variant="outline">
              <Download className="size-3 mr-1" />
              {language === 'en' ? 'Get' : 'Obtenir'}
            </Button>
          </div>
        </div>
      </Card>

      <Card className="p-4">
        <h4 className="mb-2">{t.insights}</h4>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex gap-2">
            <span className="text-blue-600">•</span>
            <span>{t.insight1}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-blue-600">•</span>
            <span>{t.insight2}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-blue-600">•</span>
            <span>{t.insight3}</span>
          </li>
        </ul>
      </Card>
    </div>
  );
}
