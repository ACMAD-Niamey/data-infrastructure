import { useEffect, useState } from 'react';
import React from 'react';
import {
  CloudSun, Droplets, Waves, Thermometer, Wheat,
  Users, AlertTriangle, Layers, MoreHorizontal,
} from 'lucide-react';
import { catalogBaseUrl } from '../config/api';

export type HazardCategory = {
  key: string;
  label: string;
  icon: React.ReactNode;
};

type RemoteCategory = {
  key: string;
  label: string;
  icon_url: string | null;
  order: number;
};

// Lucide fallback icons keyed by category slug
const ICON_FALLBACK: Record<string, React.ReactNode> = {
  weather:     React.createElement(CloudSun,      { className: 'size-5' }),
  drought:     React.createElement(Droplets,      { className: 'size-5' }),
  flood:       React.createElement(Waves,         { className: 'size-5' }),
  heat:        React.createElement(Thermometer,   { className: 'size-5' }),
  agriculture: React.createElement(Wheat,         { className: 'size-5' }),
  exposure:    React.createElement(Users,         { className: 'size-5' }),
  impact:      React.createElement(AlertTriangle, { className: 'size-5' }),
  boundary:    React.createElement(Layers,        { className: 'size-5' }),
};

const OTHER_CATEGORY: HazardCategory = {
  key:   'other',
  label: 'Other',
  icon:  React.createElement(MoreHorizontal, { className: 'size-5' }),
};

// Hardcoded fallback used on first render and when the API is unreachable
const FALLBACK_CATEGORIES: HazardCategory[] = [
  { key: 'weather',     label: 'Weather',         icon: ICON_FALLBACK.weather },
  { key: 'drought',     label: 'Drought',         icon: ICON_FALLBACK.drought },
  { key: 'flood',       label: 'Flood',           icon: ICON_FALLBACK.flood },
  { key: 'heat',        label: 'Heat',            icon: ICON_FALLBACK.heat },
  { key: 'agriculture', label: 'Agriculture',     icon: ICON_FALLBACK.agriculture },
  { key: 'exposure',    label: 'Exposure',        icon: ICON_FALLBACK.exposure },
  { key: 'impact',      label: 'Impact',          icon: ICON_FALLBACK.impact },
  { key: 'boundary',    label: 'Boundary Layers', icon: ICON_FALLBACK.boundary },
  OTHER_CATEGORY,
];

export function useHazardCategories(): HazardCategory[] {
  const [categories, setCategories] = useState<HazardCategory[]>(FALLBACK_CATEGORIES);

  useEffect(() => {
    fetch(`${catalogBaseUrl}/api/catalog/hazard-categories/`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json() as Promise<RemoteCategory[]>;
      })
      .then((data) => {
        const resolved: HazardCategory[] = data.map((c) => ({
          key:   c.key,
          label: c.label,
          icon:  c.icon_url
            ? React.createElement('img', { src: c.icon_url, className: 'size-5', alt: c.label })
            : (ICON_FALLBACK[c.key] ?? React.createElement(MoreHorizontal, { className: 'size-5' })),
        }));
        setCategories([...resolved, OTHER_CATEGORY]);
      })
      .catch(() => {
        // Keep FALLBACK_CATEGORIES — API down or not set up yet
      });
  }, []);

  return categories;
}
