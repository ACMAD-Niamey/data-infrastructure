import { useState } from 'react';
import { Language } from '../App';
import { Search, MapPin, X } from 'lucide-react';
import { Input } from './ui/input';
import { Card } from './ui/card';

interface SearchBarProps {
  language: Language;
  onLocationSelect: (location: { name: string; coords: [number, number] }) => void;
}

const translations = {
  en: {
    search: 'Search location...',
    noResults: 'No results found',
    popularLocations: 'Popular Locations'
  },
  fr: {
    search: 'Rechercher un emplacement...',
    noResults: 'Aucun résultat trouvé',
    popularLocations: 'Emplacements Populaires'
  }
};

const locations = [
  { name: 'Market District', nameFr: 'Quartier du Marché', coords: [13.5127, 2.1128] as [number, number] },
  { name: 'School Compound', nameFr: 'Enceinte Scolaire', coords: [13.5200, 2.1050] as [number, number] },
  { name: 'Residential Area', nameFr: 'Zone Résidentielle', coords: [13.5050, 2.1200] as [number, number] },
  { name: 'Park Zone', nameFr: 'Zone du Parc', coords: [13.5150, 2.1100] as [number, number] },
  { name: 'Informal Settlement', nameFr: 'Quartier Informel', coords: [13.5080, 2.1180] as [number, number] },
  { name: 'Bus Station', nameFr: 'Gare Routière', coords: [13.5180, 2.1180] as [number, number] },
  { name: 'Community Center', nameFr: 'Centre Communautaire', coords: [13.5220, 2.1080] as [number, number] },
  { name: 'Industrial Area', nameFr: 'Zone Industrielle', coords: [13.5100, 2.1050] as [number, number] }
];

export function SearchBar({ language, onLocationSelect }: SearchBarProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [showResults, setShowResults] = useState(false);
  const t = translations[language];

  const filteredLocations = locations.filter(loc => {
    const name = language === 'en' ? loc.name : loc.nameFr;
    return name.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const handleSelect = (location: typeof locations[0]) => {
    const name = language === 'en' ? location.name : location.nameFr;
    onLocationSelect({ name, coords: location.coords });
    setSearchTerm('');
    setShowResults(false);
  };

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
        <Input
          type="text"
          placeholder={t.search}
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setShowResults(true);
          }}
          onFocus={() => setShowResults(true)}
          className="pl-9 pr-9"
        />
        {searchTerm && (
          <button
            onClick={() => {
              setSearchTerm('');
              setShowResults(false);
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      {showResults && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setShowResults(false)}
          />
          <Card className="absolute top-full mt-2 w-full z-20 max-h-64 overflow-y-auto">
            {filteredLocations.length > 0 ? (
              <div className="p-2">
                {!searchTerm && (
                  <p className="text-xs text-gray-500 px-2 py-1 mb-1">
                    {t.popularLocations}
                  </p>
                )}
                {filteredLocations.map((location, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelect(location)}
                    className="w-full flex items-center gap-2 px-2 py-2 hover:bg-gray-100 rounded text-left"
                  >
                    <MapPin className="size-4 text-green-600" />
                    <span className="text-sm">
                      {language === 'en' ? location.name : location.nameFr}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-sm text-gray-500">
                {t.noResults}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
