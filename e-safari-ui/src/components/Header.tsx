import { NavLink } from 'react-router-dom';
import { Language } from '../types';
import { Button } from './ui/button';
import { Globe, Home, Leaf, Map, Info, Users, MessageSquare } from 'lucide-react';
import { InfoModal } from './InfoModal';
import acmadLogo from './images/acmadLogo.svg';
import ebaFundLogo from './images/Global-EBA-Fund-Logo.png';
import '../styles/header.css';

interface HeaderProps {
  language: Language;
  onLanguageChange: (lang: Language) => void;
}

const navItems = [
  { to: '/home',     labelEn: 'Home',      labelFr: 'Accueil',     icon: Home,          end: false },
  { to: '/geoportal', labelEn: 'Geoportal', labelFr: 'Géoportail',  icon: Map,           end: false },
  { to: '/about',    labelEn: 'About',     labelFr: 'À propos',    icon: Info,          end: false },
  { to: '/partners', labelEn: 'Partners',  labelFr: 'Partenaires', icon: Users,         end: false },
  { to: '/feedback', labelEn: 'Feedback',  labelFr: 'Retour',      icon: MessageSquare, end: false },
] as const;

export function Header({ language, onLanguageChange }: HeaderProps) {
  return (
    <header className="bg-gradient-to-r from-green-700 to-green-600 text-white shadow-lg">
      <div className="px-4 py-2 lg:px-6 lg:py-2 flex items-center justify-between gap-4">

        {/* Left — branding */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="logo">
            <img src={acmadLogo} width="45" height="45" />
          </div>
          <div className="bg-white/10 p-1.5 rounded-lg backdrop-blur-sm">
            <Leaf className="size-5 lg:size-6" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-base lg:text-lg font-bold leading-tight">e-SAFARI</h1>
            <p className="text-xs text-white/80 leading-tight">Heat &amp; Green Cover</p>
          </div>
        </div>

        {/* Center — nav links */}
        <nav className="hidden lg:flex items-center gap-0.5">
          {navItems.map(({ to, labelEn, labelFr, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition-colors ${
                  isActive
                    ? 'text-white border-b-2 border-white font-medium'
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`
              }
            >
              <Icon className="size-4" />
              {language === 'fr' ? labelFr : labelEn}
            </NavLink>
          ))}
        </nav>

        {/* Right — actions */}
        <div className="flex items-center gap-2 shrink-0">
          <InfoModal language={language} />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onLanguageChange(language === 'en' ? 'fr' : 'en')}
            className="text-white hover:bg-white/10"
          >
            <Globe className="size-4 mr-1" />
            {language === 'en' ? 'FR' : 'EN'}
          </Button>
          <div className="hidden lg:block logo shrink-0">
            <img src={ebaFundLogo} height="45" style={{ height: '45px', width: 'auto' }} />
          </div>
        </div>

      </div>
    </header>
  );
}
