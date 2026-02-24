import { Language } from '../App';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Info } from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';

interface InfoModalProps {
  language: Language;
}

const translations = {
  en: {
    title: 'About the e-SAFARI Dashboard',
    aboutProject: 'About the Project',
    aboutText: 'The e-SAFARI project generates actionable scientific evidence and provides user-friendly tools to enable the mainstreaming of nature-based solutions across policy, planning, and civil society in African cities facing climate extremes.',
    dataSources: 'Data Sources',
    heatData: 'Heat Map Data',
    heatDataDesc: 'Surface temperature measurements derived from satellite thermal imagery and ground sensors. Shows real-time and historical heat distribution across Niamey.',
    greenCover: 'Green Cover Data',
    greenCoverDesc: 'Vegetation coverage calculated from multi-spectral satellite imagery (NDVI analysis). Identifies tree canopy, grassland, and bare soil areas.',
    satelliteData: 'Satellite Imagery',
    satelliteDataDesc: 'High-resolution imagery from Landsat 8/9 (30m), Sentinel-2 (10m), and PlanetScope (3m). Updated bi-weekly with cloud cover filtering.',
    modeledData: 'Climate Projections',
    modeledDataDesc: 'Temperature and heatwave projections based on RCP 4.5 and RCP 8.5 scenarios. Models urban heat island effects and future climate conditions through 2050.',
    pointData: 'Field Measurements',
    pointDataDesc: 'Community-collected temperature readings comparing sun-exposed and tree-shaded locations. Demonstrates real cooling benefits of urban trees.',
    methodology: 'Methodology',
    methodologyText: 'Data integration combines remote sensing, climate modeling, and participatory community science. All measurements are validated and quality-controlled before visualization.',
    contact: 'Contact & Support',
    contactText: 'For questions or data access requests, please contact the e-SAFARI team.'
  },
  fr: {
    title: 'À Propos du Tableau de Bord e-SAFARI',
    aboutProject: 'À Propos du Projet',
    aboutText: 'Le projet e-SAFARI génère des preuves scientifiques exploitables et fournit des outils conviviaux pour permettre l\'intégration de solutions basées sur la nature dans les politiques, la planification et la société civile des villes africaines confrontées aux extrêmes climatiques.',
    dataSources: 'Sources de Données',
    heatData: 'Données de Chaleur',
    heatDataDesc: 'Mesures de température de surface dérivées d\'images thermiques satellitaires et de capteurs au sol. Affiche la distribution de chaleur en temps réel et historique à Niamey.',
    greenCover: 'Données de Couverture Verte',
    greenCoverDesc: 'Couverture végétale calculée à partir d\'images satellitaires multispectrales (analyse NDVI). Identifie la canopée, les prairies et les zones de sol nu.',
    satelliteData: 'Imagerie Satellite',
    satelliteDataDesc: 'Imagerie haute résolution de Landsat 8/9 (30m), Sentinel-2 (10m) et PlanetScope (3m). Mise à jour toutes les deux semaines avec filtrage de la couverture nuageuse.',
    modeledData: 'Projections Climatiques',
    modeledDataDesc: 'Projections de température et de canicule basées sur les scénarios RCP 4.5 et RCP 8.5. Modélise les effets d\'îlot de chaleur urbain et les conditions climatiques futures jusqu\'en 2050.',
    pointData: 'Mesures de Terrain',
    pointDataDesc: 'Relevés de température collectés par la communauté comparant les emplacements exposés au soleil et ombragés par les arbres. Démontre les avantages réels de refroidissement des arbres urbains.',
    methodology: 'Méthodologie',
    methodologyText: 'L\'intégration des données combine la télédétection, la modélisation climatique et la science communautaire participative. Toutes les mesures sont validées et contrôlées avant visualisation.',
    contact: 'Contact & Support',
    contactText: 'Pour des questions ou des demandes d\'accès aux données, veuillez contacter l\'équipe e-SAFARI.'
  }
};

export function InfoModal({ language }: InfoModalProps) {
  const t = translations[language];

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-white hover:bg-white/10">
          <Info className="size-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{t.title}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[70vh] pr-4">
          <div className="space-y-6">
            <div>
              <h3 className="mb-2">{t.aboutProject}</h3>
              <p className="text-sm text-gray-600">{t.aboutText}</p>
            </div>

            <div>
              <h3 className="mb-3">{t.dataSources}</h3>
              <div className="space-y-4">
                <div>
                  <h4 className="text-red-600 mb-1">{t.heatData}</h4>
                  <p className="text-sm text-gray-600">{t.heatDataDesc}</p>
                </div>

                <div>
                  <h4 className="text-green-600 mb-1">{t.greenCover}</h4>
                  <p className="text-sm text-gray-600">{t.greenCoverDesc}</p>
                </div>

                <div>
                  <h4 className="text-blue-600 mb-1">{t.satelliteData}</h4>
                  <p className="text-sm text-gray-600">{t.satelliteDataDesc}</p>
                </div>

                <div>
                  <h4 className="text-purple-600 mb-1">{t.modeledData}</h4>
                  <p className="text-sm text-gray-600">{t.modeledDataDesc}</p>
                </div>

                <div>
                  <h4 className="text-orange-600 mb-1">{t.pointData}</h4>
                  <p className="text-sm text-gray-600">{t.pointDataDesc}</p>
                </div>
              </div>
            </div>

            <div>
              <h3 className="mb-2">{t.methodology}</h3>
              <p className="text-sm text-gray-600">{t.methodologyText}</p>
            </div>

            <div>
              <h3 className="mb-2">{t.contact}</h3>
              <p className="text-sm text-gray-600">{t.contactText}</p>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
