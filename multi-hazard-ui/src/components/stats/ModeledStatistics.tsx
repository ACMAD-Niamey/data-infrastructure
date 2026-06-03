import { Language } from '../../App';
import { Card } from '../ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Brain, TrendingUp, AlertCircle } from 'lucide-react';
import { TimeSeriesSelector } from '../TimeSeriesSelector';

interface ModeledStatisticsProps {
  language: Language;
  selectedYear: string;
  onYearChange: (year: string) => void;
}

const translations = {
  en: {
    title: 'Climate Model Projections',
    baseline: 'Baseline (2024)',
    projection2030: '2030 Projection',
    projection2050: '2050 Projection',
    heatwaveIncrease: 'Heatwave Increase',
    temperatureTrend: 'Temperature Trend',
    year: 'Year',
    avgTemp: 'Avg Temp (°C)',
    heatwaveDays: 'Heatwave Days',
    insights: 'Model Predictions',
    insight1: 'Average temperatures projected to rise 3.2°C by 2050',
    insight2: 'Heatwave days (>45°C) will increase from 87 to 140 annually',
    insight3: 'Night-time cooling will decrease, affecting health recovery'
  },
  fr: {
    title: 'Projections du Modèle Climatique',
    baseline: 'Référence (2024)',
    projection2030: 'Projection 2030',
    projection2050: 'Projection 2050',
    heatwaveIncrease: 'Augmentation Canicules',
    temperatureTrend: 'Tendance de Température',
    year: 'Année',
    avgTemp: 'Temp Moy (°C)',
    heatwaveDays: 'Jours de Canicule',
    insights: 'Prédictions du Modèle',
    insight1: 'Températures moyennes augmenteront de 3,2°C d\'ici 2050',
    insight2: 'Les jours de canicule (>45°C) passeront de 87 à 140 par an',
    insight3: 'Le refroidissement nocturne diminuera, affectant la santé'
  }
};

const trendData = [
  { year: 2024, temp: 44.2, heatwaveDays: 87 },
  { year: 2026, temp: 44.8, heatwaveDays: 95 },
  { year: 2028, temp: 45.3, heatwaveDays: 103 },
  { year: 2030, temp: 45.9, heatwaveDays: 112 },
  { year: 2035, temp: 46.5, heatwaveDays: 122 },
  { year: 2040, temp: 46.9, heatwaveDays: 130 },
  { year: 2045, temp: 47.2, heatwaveDays: 135 },
  { year: 2050, temp: 47.4, heatwaveDays: 140 }
];

export function ModeledStatistics({ language, selectedYear, onYearChange }: ModeledStatisticsProps) {
  const t = translations[language];

  return (
    <div className="space-y-4">
      <div>
        <h3>{t.title}</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Brain className="size-4 text-blue-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.baseline}</p>
              <p className="text-lg text-blue-600 mt-1">44.2°C</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <TrendingUp className="size-4 text-purple-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.projection2030}</p>
              <p className="text-lg text-purple-600 mt-1">45.9°C</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="size-4 text-red-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.projection2050}</p>
              <p className="text-lg text-red-600 mt-1">47.4°C</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <TrendingUp className="size-4 text-orange-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.heatwaveIncrease}</p>
              <p className="text-lg text-orange-600 mt-1">+61%</p>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <h4 className="mb-3">{t.temperatureTrend}</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" />
            <YAxis yAxisId="left" domain={[43, 48]} label={{ value: t.avgTemp, angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" domain={[80, 150]} label={{ value: t.heatwaveDays, angle: 90, position: 'insideRight' }} />
            <Tooltip />
            <Legend />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="temp" 
              stroke="#7c3aed" 
              strokeWidth={2}
              name={t.avgTemp}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="heatwaveDays" 
              stroke="#f97316" 
              strokeWidth={2}
              name={t.heatwaveDays}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card className="p-4">
        <h4 className="mb-2">{t.insights}</h4>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex gap-2">
            <span className="text-purple-600">•</span>
            <span>{t.insight1}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-purple-600">•</span>
            <span>{t.insight2}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-purple-600">•</span>
            <span>{t.insight3}</span>
          </li>
        </ul>
      </Card>

      <Card className="p-4">
        <TimeSeriesSelector
          language={language}
          selectedYear={selectedYear}
          onYearChange={onYearChange}
        />
      </Card>
    </div>
  );
}