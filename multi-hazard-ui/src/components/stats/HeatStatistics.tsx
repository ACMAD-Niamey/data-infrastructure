import { Language } from '../../App';
import { Card } from '../ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, AlertTriangle, Thermometer } from 'lucide-react';

interface HeatStatisticsProps {
  language: Language;
}

const translations = {
  en: {
    title: 'Heat Distribution Analysis',
    avgTemp: 'Average Temperature',
    maxTemp: 'Maximum Temperature',
    heatwaveDays: 'Heatwave Days (>45°C)',
    riskLevel: 'Risk Level',
    high: 'High',
    projection: '2050 Projection',
    tempByZone: 'Temperature by Zone',
    zone: 'Zone',
    current: 'Current',
    projected: 'Projected 2050',
    insights: 'Key Insights',
    insight1: 'Informal settlements experience highest heat exposure',
    insight2: 'Heatwave days expected to increase by 60% by 2050',
    insight3: 'Zones with <20% tree cover exceed 45°C regularly'
  },
  fr: {
    title: 'Analyse de Distribution de Chaleur',
    avgTemp: 'Température Moyenne',
    maxTemp: 'Température Maximum',
    heatwaveDays: 'Jours de Canicule (>45°C)',
    riskLevel: 'Niveau de Risque',
    high: 'Élevé',
    projection: 'Projection 2050',
    tempByZone: 'Température par Zone',
    zone: 'Zone',
    current: 'Actuel',
    projected: 'Projeté 2050',
    insights: 'Observations Clés',
    insight1: 'Les quartiers informels subissent la plus forte exposition',
    insight2: 'Les jours de canicule augmenteront de 60% d\'ici 2050',
    insight3: 'Les zones avec <20% d\'arbres dépassent 45°C régulièrement'
  }
};

const chartData = [
  { zone: 'A', current: 44.5, projected: 47.2 },
  { zone: 'B', current: 43.2, projected: 45.8 },
  { zone: 'C', current: 45.8, projected: 48.5 },
  { zone: 'D', current: 42.1, projected: 44.6 },
  { zone: 'E', current: 44.9, projected: 47.6 }
];

export function HeatStatistics({ language }: HeatStatisticsProps) {
  const t = translations[language];

  return (
    <div className="space-y-4">
      <div>
        <h3>{t.title}</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Thermometer className="size-4 text-orange-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.avgTemp}</p>
              <p className="text-lg text-orange-600 mt-1">44.2°C</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <TrendingUp className="size-4 text-red-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.maxTemp}</p>
              <p className="text-lg text-red-600 mt-1">46.8°C</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="size-4 text-amber-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.heatwaveDays}</p>
              <p className="text-lg text-amber-600 mt-1">87 days</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="size-4 text-red-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.riskLevel}</p>
              <p className="text-lg text-red-600 mt-1">{t.high}</p>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <h4 className="mb-3">{t.tempByZone}</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="zone" />
            <YAxis domain={[40, 50]} />
            <Tooltip />
            <Legend />
            <Bar dataKey="current" fill="#f97316" name={t.current} />
            <Bar dataKey="projected" fill="#dc2626" name={t.projected} />
          </BarChart>
        </ResponsiveContainer>
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
