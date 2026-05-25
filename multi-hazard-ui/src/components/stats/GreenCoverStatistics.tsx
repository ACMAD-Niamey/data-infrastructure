import { Language } from '../../App';
import { Card } from '../ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Trees, TrendingDown, Target } from 'lucide-react';

interface GreenCoverStatisticsProps {
  language: Language;
}

const translations = {
  en: {
    title: 'Green Cover Analysis',
    coverage: 'Current Coverage',
    deficit: 'Coverage Deficit',
    target: 'WHO Target',
    coolingPotential: 'Cooling Potential',
    distribution: 'Coverage Distribution',
    high: 'High (>60%)',
    medium: 'Medium (30-60%)',
    low: 'Low (<30%)',
    insights: 'Key Insights',
    insight1: 'Only 18% of city meets WHO green space target (9m²/person)',
    insight2: 'Informal settlements have <10% tree canopy coverage',
    insight3: 'Adding 25% tree cover could reduce temperatures by 3-5°C'
  },
  fr: {
    title: 'Analyse de Couverture Verte',
    coverage: 'Couverture Actuelle',
    deficit: 'Déficit de Couverture',
    target: 'Cible OMS',
    coolingPotential: 'Potentiel de Refroidissement',
    distribution: 'Distribution de Couverture',
    high: 'Élevé (>60%)',
    medium: 'Moyen (30-60%)',
    low: 'Faible (<30%)',
    insights: 'Observations Clés',
    insight1: 'Seulement 18% de la ville atteint l\'objectif OMS (9m²/personne)',
    insight2: 'Les quartiers informels ont <10% de couverture arborée',
    insight3: 'Ajouter 25% d\'arbres pourrait réduire de 3-5°C'
  }
};

const coverageData = [
  { name: 'High', value: 22, color: '#15803d' },
  { name: 'Medium', value: 38, color: '#16a34a' },
  { name: 'Low', value: 40, color: '#86efac' }
];

export function GreenCoverStatistics({ language }: GreenCoverStatisticsProps) {
  const t = translations[language];

  return (
    <div className="space-y-4">
      <div>
        <h3>{t.title}</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Trees className="size-4 text-green-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.coverage}</p>
              <p className="text-lg text-green-600 mt-1">28.4%</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <TrendingDown className="size-4 text-amber-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.deficit}</p>
              <p className="text-lg text-amber-600 mt-1">71.6%</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Target className="size-4 text-blue-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.target}</p>
              <p className="text-lg text-blue-600 mt-1">9m²/p</p>
            </div>
          </div>
        </Card>

        <Card className="p-3">
          <div className="flex items-start gap-2">
            <Trees className="size-4 text-cyan-600 mt-1" />
            <div>
              <p className="text-xs text-gray-500">{t.coolingPotential}</p>
              <p className="text-lg text-cyan-600 mt-1">-3 to -5°C</p>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <h4 className="mb-3">{t.distribution}</h4>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={coverageData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={70}
              fill="#8884d8"
              dataKey="value"
            >
              {coverageData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
        <div className="mt-3 space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#15803d]" />
            <span>{t.high}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#16a34a]" />
            <span>{t.medium}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-[#86efac]" />
            <span>{t.low}</span>
          </div>
        </div>
      </Card>

      <Card className="p-4">
        <h4 className="mb-2">{t.insights}</h4>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex gap-2">
            <span className="text-green-600">•</span>
            <span>{t.insight1}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-green-600">•</span>
            <span>{t.insight2}</span>
          </li>
          <li className="flex gap-2">
            <span className="text-green-600">•</span>
            <span>{t.insight3}</span>
          </li>
        </ul>
      </Card>
    </div>
  );
}
