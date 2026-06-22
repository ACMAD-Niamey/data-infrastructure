import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Map, ArrowRight,
  Thermometer, Leaf, Building2, Users, Globe, Layers, CalendarDays, BarChart3,
  Cloud, ShieldCheck, Handshake,
} from 'lucide-react';
import type { Language } from './types';
import { getProjectSlug } from './services/catalogLayersApi';
import type { LucideProps } from 'lucide-react';

interface AboutProps {
  language: Language;
}

type IconComponent = React.ComponentType<LucideProps>;

const iconMap: Record<string, IconComponent> = {
  thermometer: Thermometer,
  leaf: Leaf,
  'building-2': Building2,
  users: Users,
  globe: Globe,
  layers: Layers,
  'calendar-days': CalendarDays,
  'bar-chart-3': BarChart3,
  cloud: Cloud,
  'shield-check': ShieldCheck,
  handshake: Handshake,
};

const iconColors = ['#ea580c', '#16803d', '#ea580c', '#16803d', '#2563eb', '#16803d', '#ea580c', '#2563eb'];
const iconBgs   = ['#fff7ed', '#f0fdf4', '#fff7ed', '#f0fdf4', '#eff6ff', '#f0fdf4', '#fff7ed', '#eff6ff'];

const translations = {
  en: {
    openGeoportal: 'Open Geoportal',
    provides: 'What e-SAFARI provides',
    builtFor: 'Built for',
    howItWorks: 'How it works',
    audiences: [
      { label: 'Climate services', icon: Cloud },
      { label: 'Urban planners',   icon: Building2 },
      { label: 'Policy teams',     icon: ShieldCheck },
      { label: 'Project partners', icon: Handshake },
    ],
    steps: [
      { n: 1, title: 'Select a country',         desc: 'Choose a country and urban area of interest.' },
      { n: 2, title: 'Explore layers',            desc: 'Visualize heat, buildings, land use and green cover.' },
      { n: 3, title: 'Compare scenario years',    desc: 'Analyze current and future scenarios side by side.' },
      { n: 4, title: 'Use evidence for action',   desc: 'Turn insights into informed decisions and impact.' },
    ],
  },
  fr: {
    openGeoportal: 'Ouvrir le Géoportail',
    provides: 'Ce que e-SAFARI fournit',
    builtFor: 'Conçu pour',
    howItWorks: 'Comment ça marche',
    audiences: [
      { label: 'Services climatiques', icon: Cloud },
      { label: 'Urbanistes',           icon: Building2 },
      { label: 'Équipes politiques',   icon: ShieldCheck },
      { label: 'Partenaires',          icon: Handshake },
    ],
    steps: [
      { n: 1, title: 'Sélectionner un pays',          desc: "Choisissez un pays et une zone urbaine d'intérêt." },
      { n: 2, title: 'Explorer les couches',           desc: 'Visualisez la chaleur, les bâtiments et la couverture verte.' },
      { n: 3, title: 'Comparer les années',            desc: 'Analysez les scénarios actuels et futurs côte à côte.' },
      { n: 4, title: "Utiliser les données",           desc: "Transformez les informations en décisions éclairées." },
    ],
  },
};

interface Feature { title: string; description: string; icon_name: string; }

export function About({ language }: AboutProps) {
  const t = translations[language];
  const navigate = useNavigate();
  const slug = getProjectSlug();

  const [aboutTitle, setAboutTitle]       = useState('');
  const [aboutIntro, setAboutIntro]       = useState('');
  const [aboutDesc, setAboutDesc]         = useState('');
  const [aboutImageUrl, setAboutImageUrl] = useState<string | null>(null);
  const [features, setFeatures]           = useState<Feature[]>([]);

  useEffect(() => {
    fetch(`/api/catalog/projects/${slug}/config/`)
      .then((r) => r.json())
      .then((data) => {
        setAboutTitle(data.about_title ?? '');
        setAboutIntro(data.about_intro ?? '');
        setAboutDesc(data.about_description ?? '');
        setAboutImageUrl(data.about_image_url ?? null);
        setFeatures(data.features ?? []);
      })
      .catch(() => {});
  }, [slug]);

  return (
    <div style={{ overflowY: 'auto', height: '100%', backgroundColor: '#fff' }}>

      {/* ── Hero: two-column ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 380, backgroundColor: '#fff' }}>
        {/* Left */}
        <div style={{ padding: '52px 48px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {aboutTitle && (
            <>
              <h1 style={{ fontSize: 'clamp(1.6rem, 3vw, 2.2rem)', fontWeight: 800, color: '#111827', marginBottom: 10 }}>
                {aboutTitle}
              </h1>
              <div style={{ width: 44, height: 3, backgroundColor: '#16803d', borderRadius: 2, marginBottom: 20 }} />
            </>
          )}
          {aboutIntro && (
            <p style={{ fontSize: 16, fontWeight: 600, color: '#16803d', marginBottom: 14, lineHeight: 1.5 }}>
              {aboutIntro}
            </p>
          )}
          {aboutDesc && (
            <p style={{ fontSize: 14, color: '#374151', lineHeight: 1.7, marginBottom: 28, maxWidth: 440 }}>
              {aboutDesc}
            </p>
          )}
          <button
            type="button"
            onClick={() => navigate('/geoportal')}
            style={{
              alignSelf: 'flex-start',
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '11px 24px', borderRadius: 8, border: 'none',
              backgroundColor: '#16803d', color: 'white',
              fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}
          >
            <Map style={{ width: 15, height: 15 }} />
            {t.openGeoportal}
            <ArrowRight style={{ width: 15, height: 15 }} />
          </button>
        </div>

        {/* Right — image or placeholder */}
        <div style={{ overflow: 'hidden', minHeight: 340 }}>
          {aboutImageUrl ? (
            <img
              src={aboutImageUrl}
              alt=""
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
          ) : (
            <div style={{ width: '100%', height: '100%', backgroundColor: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Globe style={{ width: 64, height: 64, color: '#bbf7d0' }} />
            </div>
          )}
        </div>
      </div>

      {/* ── What e-SAFARI provides ── */}
      {features.length > 0 && (
        <div style={{ backgroundColor: '#f9fafb', padding: '52px 48px' }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', marginBottom: 28 }}>{t.provides}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            {features.map((f, i) => {
              const Icon: IconComponent = iconMap[f.icon_name] ?? Leaf;
              const color = iconColors[i % iconColors.length];
              const bg    = iconBgs[i % iconBgs.length];
              return (
                <div key={i} style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: 12, padding: '20px 18px' }}>
                  <div style={{ width: 44, height: 44, borderRadius: '50%', backgroundColor: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
                    <Icon style={{ width: 22, height: 22, color }} />
                  </div>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: '#111827', marginBottom: 6 }}>{f.title}</h3>
                  <p style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.55 }}>{f.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Built for + How it works ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0, borderTop: '1px solid #e5e7eb' }}>
        {/* Built for */}
        <div style={{ padding: '40px 48px', borderRight: '1px solid #e5e7eb' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 24 }}>{t.builtFor}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {t.audiences.map(({ label, icon: Icon }, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 52, height: 52, borderRadius: '50%', border: '1.5px solid #16803d', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon style={{ width: 22, height: 22, color: '#16803d' }} />
                </div>
                <span style={{ fontSize: 12, color: '#374151', textAlign: 'center' }}>{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* How it works */}
        <div style={{ padding: '40px 48px' }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 24 }}>{t.howItWorks}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {t.steps.map(({ n, title, desc }) => (
              <div key={n} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, textAlign: 'center' }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', backgroundColor: '#16803d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 14, fontWeight: 700 }}>
                  {n}
                </div>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{title}</span>
                <span style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.5 }}>{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}
