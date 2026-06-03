import { Language } from '../types';
import { Button } from './ui/button';
import { Globe, Leaf } from 'lucide-react';
import { InfoModal } from './InfoModal';
import acmadLogo from './images/acmadLogo.svg';
import '../styles/header.css';

interface HeaderProps {
  language: Language;
  onLanguageChange: (lang: Language) => void;
}

const translations = {
  en: {
    title: 'e-SAFARI Heat & Green Cover Dashboard',
    subtitle: 'Niamey, Niger',
    tagline: 'Evidence-based urban cooling for climate resilience'
  },
  fr: {
    title: 'Tableau de bord e-SAFARI Chaleur & Couverture Verte',
    subtitle: 'Niamey, Niger',
    tagline: 'Refroidissement urbain basé sur des preuves pour la résilience climatique'
  }
};

export function Header({ language, onLanguageChange }: HeaderProps) {
  const t = translations[language];
  
  return (
    <header className="bg-gradient-to-r from-green-700 to-green-600 text-white shadow-lg">
      <div className="px-4 py-2 lg:px-6 lg:py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-white/10 p-1.5 rounded-lg backdrop-blur-sm">
              <Leaf className="size-5 lg:size-6" />
            </div>
            <div>
              <h1 className="text-base lg:text-xl tracking-tight">{t.title}</h1>
              <p className="text-xs lg:text-sm text-green-100 mt-0.5">{t.subtitle}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <InfoModal language={language} />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onLanguageChange(language === 'en' ? 'fr' : 'en')}
              className="text-white hover:bg-white/10"
            >
              <Globe className="size-4 mr-2" />
              {language === 'en' ? 'FR' : 'EN'}
            </Button>
            <div className="logo">
              <img src={acmadLogo} width="45" height="45" />
            </div>
          </div>
        </div>
        
        <p className="text-xs text-green-50 mt-1 hidden lg:block">
          {t.tagline}
        </p>

      </div>
    </header>
  );
}