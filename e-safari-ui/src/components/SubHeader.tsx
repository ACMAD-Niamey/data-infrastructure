import type React from 'react';
import type { Language } from '../types';

export interface CountryOption {
  value: string;
  label: string;
  bounds: { west: number; south: number; east: number; north: number };
}

interface SubHeaderProps {
  countries: CountryOption[];
  selectedCountry: CountryOption | null;
  onCountryChange: (country: CountryOption | null) => void;
  language: Language;
}

const translations = {
  en: {
    country: 'Country',
    all: 'All countries',
    tagline: 'Evidence-based urban cooling for climate resilience',
  },
  fr: {
    country: 'Pays',
    all: 'Tous les pays',
    tagline: 'Refroidissement urbain basé sur des preuves pour la résilience climatique',
  },
};

export function SubHeader({ countries, selectedCountry, onCountryChange, language }: SubHeaderProps) {
  const t = translations[language];

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const found = countries.find((c) => c.value === e.target.value) ?? null;
    onCountryChange(found);
  };

  return (
    <div className="flex items-center gap-4 px-4 py-2 lg:px-6 bg-white border-b border-gray-200 text-sm">
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-gray-500 font-medium">{t.country}</span>
        <select
          value={selectedCountry?.value ?? ''}
          onChange={handleChange}
          className="border border-gray-300 rounded px-2 py-1 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-green-600"
        >
          <option value="">{t.all}</option>
          {countries.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
      <span className="hidden lg:block text-gray-400">|</span>
      <p className="hidden lg:block text-xs text-green-700">{t.tagline}</p>
    </div>
  );
}
