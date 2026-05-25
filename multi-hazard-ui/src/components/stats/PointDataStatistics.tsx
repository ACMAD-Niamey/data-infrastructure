import { Language } from '../../App';
import { Card } from '../ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { MapPin, Users, Thermometer, TrendingDown } from 'lucide-react';
import { pointData } from '../../data/pointData';

interface PointDataStatisticsProps {
  language: Language;
}

const translations = {
  en: {
    title: 'Field Measurement Analysis',
    totalPoints: 'Measurement Points',
    avgSun: 'Avg in Sun',
    avgShade: 'Avg in Shade',
    avgDifference: 'Avg Cooling Effect',
    tempComparison: 'Sun vs Shade Comparison',
    location: 'Location',
    sun: 'In Sun',
    shade: 'In Shade',
    dataCollectors: 'Community Data Collectors',
    insights: 'Field Observations',
    insight1: 'Trees provide 6-8°C cooling on average',
    insight2: 'Community teams collected data from 8 strategic locations',
    insight3: 'Greatest cooling benefits observed in market and school areas'
  },
  fr: {
    title: 'Analyse des Mesures de Terrain',
    totalPoints: 'Points de Mesure',
    avgSun: 'Moy au Soleil',
    avgShade: 'Moy à l\'Ombre',
    avgDifference: 'Effet de Refroidissement',
    tempComparison: 'Comparaison Soleil vs Ombre',
    location: 'Emplacement',
    sun: 'Au Soleil',
    shade: 'À l\'Ombre',
    dataCollectors: 'Collecteurs de Données Communautaires',
    insights: 'Observations de Terrain',
    insight1: 'Les arbres procurent 6-8°C de refroidissement en moyenne',
    insight2: 'Les équipes communautaires ont collecté des données sur 8 sites',
    insight3: 'Meilleurs bénéfices observés dans les marchés et les écoles'
  }
};

export function PointDataStatistics({ language }: PointDataStatisticsProps) {
  const t = translations[language];

  const avgSunTemp = pointData.reduce((sum, p) => sum + p.sunTemp, 0) / pointData.length;
  const avgShadeTemp = pointData.reduce((sum, p) => sum + p.shadeTemp, 0) / pointData.length;
  const avgDifference = avgSunTemp - avgShadeTemp;

  const chartData = pointData.map(point => ({
    name: point.name.split(' ')[0], // Shortened names for chart
    sun: point.sunTemp,
    shade: point.shadeTemp,
    difference: point.sunTemp - point.shadeTemp
  }));

  const uniqueCollectors = [...new Set(pointData.map(p => p.collector))];

  return (
    <div className="space-y-4">
      <div>
        <h3>{t.title}</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3">
          <div className="flex items-start gap-2">
            <MapPin className="size-4 text-orange-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.totalPoints}</p>
              <p className="text-lg text-orange-600 mt-1">{pointData.length}</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Thermometer className="size-4 text-red-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.avgSun}</p>
              <p className="text-lg text-red-600 mt-1">{avgSunTemp.toFixed(1)}°C</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Thermometer className="size-4 text-cyan-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.avgShade}</p>
              <p className="text-lg text-cyan-600 mt-1">{avgShadeTemp.toFixed(1)}°C</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <TrendingDown className="size-4 text-green-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.avgDifference}</p>
              <p className="text-lg text-green-600 mt-1">-{avgDifference.toFixed(1)}°C</p>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <h4 className="mb-3">{t.tempComparison}</h4>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
            <YAxis domain={[30, 50]} />
            <Tooltip />
            <Legend />
            <Bar dataKey="sun" fill="#f97316" name={t.sun} />
            <Bar dataKey="shade" fill="#0ea5e9" name={t.shade} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card className="p-4">
        <h4 className="mb-2">{t.dataCollectors}</h4>
        <div className="space-y-2">
          {uniqueCollectors.map((collector, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm p-2 bg-orange-50 rounded">
              <Users className="size-4 text-orange-600" />
              <span>{collector}</span>
              <span className="ml-auto text-xs text-gray-500">
                {pointData.filter(p => p.collector === collector).length} {language === 'en' ? 'points' : 'points'}
              </span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h4 className="mb-2">{t.insights}</h4>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex gap-2">
            <span className="text-orange-600">•</span>
            <span>{t.insight1}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-orange-600">•</span>
            <span>{t.insight2}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-orange-600">•</span>
            <span>{t.insight3}</span>
          </li>
        </ul>
      </Card>
    </div>
  );
}
