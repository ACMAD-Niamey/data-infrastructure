import { Language } from '../App';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface TimeSeriesSelectorProps {
  language: Language;
  selectedYear: string;
  onYearChange: (year: string) => void;
}

const translations = {
  en: {
    selectYear: 'Select Year',
    baseline: 'Baseline (2024)',
    current: 'Current'
  },
  fr: {
    selectYear: 'Sélectionner l\'Année',
    baseline: 'Référence (2024)',
    current: 'Actuel'
  }
};

const years = [
  { value: '2024', labelEn: 'Current (2024)', labelFr: 'Actuel (2024)' },
  { value: '2026', labelEn: '2026', labelFr: '2026' },
  { value: '2028', labelEn: '2028', labelFr: '2028' },
  { value: '2030', labelEn: '2030', labelFr: '2030' },
  { value: '2035', labelEn: '2035', labelFr: '2035' },
  { value: '2040', labelEn: '2040', labelFr: '2040' },
  { value: '2045', labelEn: '2045', labelFr: '2045' },
  { value: '2050', labelEn: '2050', labelFr: '2050' }
];

export function TimeSeriesSelector({ language, selectedYear, onYearChange }: TimeSeriesSelectorProps) {
  const t = translations[language];

  return (
    <div className="space-y-2">
      <label className="text-sm text-gray-600">{t.selectYear}</label>
      <Select value={selectedYear} onValueChange={onYearChange}>
        <SelectTrigger>
          <SelectValue placeholder={t.selectYear} />
        </SelectTrigger>
        <SelectContent>
          {years.map((year) => (
            <SelectItem key={year.value} value={year.value}>
              {language === 'en' ? year.labelEn : year.labelFr}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
