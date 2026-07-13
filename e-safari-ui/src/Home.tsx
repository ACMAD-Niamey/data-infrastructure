import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf, ArrowRight, Map } from 'lucide-react';
import type { Language } from './types';
import type { CountryOption } from './components/SubHeader';
import { getProjectSlug } from './services/catalogLayersApi';
import { featureIconMap, featureIconColors, featureIconBgs } from './lib/featureIcons';
import type { Feature, IconComponent } from './lib/featureIcons';

interface HomeProps {
  language: Language;
}

const translations = {
  en: {
    openGeoportal: 'Open Geoportal',
    citiesLabel: 'Cities',
    countriesLabel: 'Countries',
    layersLabel: 'Data layers',
    scenarioLabel: 'Scenario analysis',
    evidenceLabel: 'Evidence for resilient planning',
    explore: 'What you can explore',
  },
  fr: {
    openGeoportal: 'Ouvrir le Géoportail',
    citiesLabel: 'Villes',
    countriesLabel: 'Pays',
    layersLabel: 'Couches de données',
    scenarioLabel: 'Analyse de scénarios',
    evidenceLabel: 'Données pour la planification résiliente',
    explore: 'Ce que vous pouvez explorer',
  },
};

export function Home({ language }: HomeProps) {
  const t = translations[language];
  const navigate = useNavigate();
  const slug = getProjectSlug();

  const [heroImageUrl, setHeroImageUrl] = useState<string | null>(null);
  const [headline, setHeadline] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [citiesCount, setCitiesCount] = useState('');
  const [layerCount, setLayerCount] = useState<number | null>(null);
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);

  useEffect(() => {
    fetch(`/api/catalog/projects/${slug}/config/`)
      .then((r) => r.json())
      .then((data) => {
        setHeroImageUrl(data.hero_image_url ?? null);
        setHeadline(data.headline ?? '');
        setSubtitle(data.subtitle ?? '');
        setCitiesCount(data.cities_count ?? '');
        setLayerCount(data.layer_count ?? null);
        setFeatures(data.features ?? []);
      })
      .catch(() => {});

    fetch(`/api/catalog/projects/${slug}/countries/`)
      .then((r) => r.json())
      .then((data: CountryOption[]) => setCountries(data))
      .catch(() => {});
  }, [slug]);

  return (
    <div style={{ overflowY: 'auto', height: '100%' }}>
      {/* Hero */}
      <div
        style={{
          position: 'relative',
          minHeight: '60vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          backgroundImage: heroImageUrl ? `url(${heroImageUrl})` : undefined,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundColor: '#14532d',
        }}
      >
        {/* Dark overlay */}
        <div style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(5, 46, 22, 0.72)' }} />

        <div style={{ position: 'relative', zIndex: 1, maxWidth: 700, padding: '60px 40px' }}>
          <h1 style={{ fontSize: 'clamp(1.75rem, 4vw, 2.75rem)', fontWeight: 800, color: 'white', lineHeight: 1.15, marginBottom: 16 }}>
            {headline}
          </h1>
          {subtitle && (
            <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.85)', marginBottom: 32, maxWidth: 520, lineHeight: 1.6 }}>
              {subtitle}
            </p>
          )}

          {/* CTA */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 48 }}>
            <button
              type="button"
              onClick={() => navigate('/geoportal')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 24px',
                borderRadius: 8,
                border: 'none',
                backgroundColor: '#16803d',
                color: 'white',
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <Map style={{ width: 15, height: 15 }} />
              {t.openGeoportal}
              <ArrowRight style={{ width: 15, height: 15 }} />
            </button>
          </div>

          {/* Stats row */}
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center' }}>
            {[
              { value: citiesCount, label: t.citiesLabel },
              { value: countries.length > 0 ? String(countries.length) : '', label: t.countriesLabel },
              { value: layerCount !== null ? String(layerCount) : '', label: t.layersLabel },
              { value: '', label: t.scenarioLabel },
              { value: '', label: t.evidenceLabel },
            ].map((stat, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
                {i > 0 && (
                  <span style={{ color: 'rgba(255,255,255,0.3)', margin: '0 14px', fontSize: 20 }}>|</span>
                )}
                <div>
                  {stat.value && (
                    <span style={{ fontSize: 20, fontWeight: 700, color: 'white', marginRight: 4 }}>{stat.value}</span>
                  )}
                  <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)' }}>{stat.label}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Feature cards */}
      {features.length > 0 && (
        <div style={{ backgroundColor: '#f9fafb', padding: '52px 40px' }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#111827', marginBottom: 28 }}>{t.explore}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 18 }}>
            {features.map((card, i) => {
              const Icon: IconComponent = featureIconMap[card.icon_name] ?? Leaf;
              const color = featureIconColors[i % featureIconColors.length];
              const bg    = featureIconBgs[i % featureIconBgs.length];
              const target = card.layer_id ? `/geoportal?layer=${encodeURIComponent(card.layer_id)}` : '/geoportal';
              return (
                <div
                  key={i}
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(target)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      navigate(target);
                    }
                  }}
                  style={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: 12,
                    padding: '24px 20px',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'none'; }}
                >
                  <div style={{ width: 44, height: 44, borderRadius: '50%', backgroundColor: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
                    <Icon style={{ width: 22, height: 22, color }} />
                  </div>
                  <h3 style={{ fontSize: 15, fontWeight: 700, color: '#111827', marginBottom: 8 }}>{card.title}</h3>
                  <p style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.55, marginBottom: 16 }}>{card.description}</p>
                  <ArrowRight style={{ width: 16, height: 16, color: '#9ca3af' }} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
