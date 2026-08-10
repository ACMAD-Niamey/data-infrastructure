import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Map, Database, Network, FileText, Droplets, CloudRain, Waves,
  ArrowRight, Sparkles, CalendarDays,
} from 'lucide-react';
import NavBar from '../components/NavBar';
import MapComponent from '../components/map.jsx';
import { useMap } from '../components/MapContext.jsx';
import { add_image_layer, remove_image_layer } from '../components/Maputils.js';
import { LegendDisplay } from '../components/LegendDisplay';
import { useCatalogLayers } from '../hooks/useCatalogLayers';
import { useHazardCategories } from '../hooks/useHazardCategories';
import { fetchDatasetAvailability, fetchDatasetVisualization } from '../services/layersApi';
import { inferCategory } from '../lib/inferCategory';

// ---------------------------------------------------------------------------
// Static page data
// ---------------------------------------------------------------------------

const exploreCards = [
  { icon: <Map className="size-8 text-hub-400" />, title: 'Geoportal', description: 'Explore interactive maps, layers, and geospatial data.', to: '/geoportal' },
  { icon: <Database className="size-8 text-hub-400" />, title: 'Data Services', description: 'Access APIs, data downloads, and programmatic services.', to: '/data-services' },
  { icon: <Network className="size-8 text-hub-400" />, title: 'Data Platforms', description: 'Access thematic platforms and partner systems.', to: '/data-platforms' },
  { icon: <FileText className="size-8 text-hub-400" />, title: 'Bulletins', description: 'Read latest advisories and situation reports.', to: '/bulletins' },
];

const mockBulletins = [
  { icon: <Droplets className="size-6 text-amber-500" />, title: 'Drought Watch Advisory – 2nd Dekad of May 2026', issued: '26 May 2026', category: 'Drought', categoryColor: 'bg-amber-100 text-amber-700' },
  { icon: <CloudRain className="size-6 text-blue-500" />, title: 'Heavy Rainfall Outlook – 27 May to 2 Jun 2026', issued: '26 May 2026', category: 'Weather', categoryColor: 'bg-blue-100 text-blue-700' },
  { icon: <Waves className="size-6 text-hub-400" />, title: 'Flood Risk Outlook – 1st to 7th June 2026', issued: '25 May 2026', category: 'Flood', categoryColor: 'bg-hub-100 text-hub-700' },
];

const partners = ['JRC', 'NORCAP', 'AU', 'ICPAC', 'WMO'];

// ---------------------------------------------------------------------------
// AI Analytics panel (placeholder)
// ---------------------------------------------------------------------------

function AIAnalyticsPanel({ legendEntries }: { legendEntries: [string, string][] }) {
  return (
    <div className="w-80 shrink-0 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-hub-400" />
          <span className="font-bold text-gray-800 text-sm">AI-powered Analytics</span>
        </div>
        <button className="text-xs font-medium border border-hub-400 text-hub-700 hover:bg-hub-100 px-3 py-1 rounded-full transition-colors">
          Chat with AI
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Hazard Severity Breakdown */}
        <div className="border border-gray-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-gray-700 mb-3">Hazard Severity Breakdown</p>
          {legendEntries.length > 0 ? (
            <>
              {/* Simple donut placeholder */}
              <div className="flex justify-center mb-3">
                <div className="relative w-28 h-28">
                  <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle cx="18" cy="18" r="14" fill="none" stroke="#e5e7eb" strokeWidth="4" />
                    {legendEntries.slice(0, 4).map((_, i) => {
                      const colors = ['#22c55e', '#eab308', '#f97316', '#ef4444'];
                      const offsets = [0, 25, 50, 75];
                      return (
                        <circle
                          key={i}
                          cx="18" cy="18" r="14"
                          fill="none"
                          stroke={colors[i] ?? '#d1d5db'}
                          strokeWidth="4"
                          strokeDasharray={`${25} ${75}`}
                          strokeDashoffset={`-${offsets[i]}`}
                        />
                      );
                    })}
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xs text-gray-400 font-medium text-center leading-tight">Coming<br />soon</span>
                  </div>
                </div>
              </div>
              <div className="space-y-1.5">
                {legendEntries.slice(0, 4).map(([label, color]) => (
                  <div key={label} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    <span className="text-xs text-gray-600">{label}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-28 gap-2">
              <div className="w-20 h-20 rounded-full border-4 border-gray-100 border-t-gray-300 animate-spin" />
              <span className="text-xs text-gray-400">Loading data…</span>
            </div>
          )}
        </div>

        {/* Risk Level */}
        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-gray-700">Risk Level</p>
            <span className="text-[10px] bg-hub-100 text-hub-700 font-medium px-2 py-0.5 rounded-full">Coming Soon</span>
          </div>
          <div className="space-y-2">
            {['High', 'Medium', 'Low', 'Minimal'].map((level, i) => {
              const widths = ['w-2/3', 'w-1/2', 'w-1/3', 'w-1/4'];
              const colors = ['bg-red-300', 'bg-orange-300', 'bg-yellow-300', 'bg-green-300'];
              return (
                <div key={level} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-14 shrink-0">{level}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div className={`${widths[i]} ${colors[i]} h-2 rounded-full opacity-60`} />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-xs text-gray-400 mt-3 text-center">AI-driven risk assessment coming soon</p>
        </div>

        {/* Trend placeholder */}
        <div className="border border-gray-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-gray-700 mb-3">30-Day Trend</p>
          <div className="h-20 bg-gray-50 rounded flex items-end gap-1 px-2 pb-2">
            {[3, 5, 4, 7, 6, 8, 5, 9, 7, 6, 8, 10].map((h, i) => (
              <div
                key={i}
                className="flex-1 bg-gray-200 rounded-t opacity-70"
                style={{ height: `${h * 8}%` }}
              />
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">Predictive analytics coming soon</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Home page
// ---------------------------------------------------------------------------

export default function Home() {
  const { mapRef } = useMap() ?? { mapRef: { current: null } };
  const { layers } = useCatalogLayers('en');
  const categories = useHazardCategories();

  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [currentDateLabel, setCurrentDateLabel] = useState<string | null>(null);
  const [legendEntries, setLegendEntries] = useState<[string, string][]>([]);
  const prevLayerIdRef = useRef<string | null>(null);
  // Layers pinned to always show on the homepage hero map, independent of the category
  // switcher (e.g. an admin-boundary overlay) — loaded once and never swapped by category changes.
  const loadedHomepageLayerIdsRef = useRef<Set<string>>(new Set());

  // Re-assert any homepage layer marked always-on-top above the map's other layers —
  // call this right after the category raster (or another homepage layer) is added.
  const pinHomepageAlwaysOnTop = (justAddedLayerId?: string) => {
    const map = mapRef?.current as any;
    if (!map) return;
    layers.forEach((l) => {
      if (l.id === justAddedLayerId || !l.ui?.display_on_homepage || !l.ui?.always_on_top) return;
      const rasterId = `raster-home-pin-${l.id}`;
      if (map.getLayer(rasterId)) map.moveLayer(rasterId);
    });
  };

  // Load every layer marked "display on homepage" once, alongside the category raster.
  useEffect(() => {
    const map = mapRef?.current as any;
    if (!map) return;

    layers
      .filter((l) => l.ui?.display_on_homepage && !loadedHomepageLayerIdsRef.current.has(l.id))
      .forEach((layer) => {
        loadedHomepageLayerIdsRef.current.add(layer.id);
        const cadence = layer.dataset.cadence;
        const rasterId = `raster-home-pin-${layer.id}`;

        fetchDatasetAvailability({ datasetId: layer.dataset.id, cadence })
          .then(({ max, options }) => {
            const date = max || options[0]?.value;
            if (!date) return null;
            return fetchDatasetVisualization({ datasetId: layer.dataset.id, cadence, date });
          })
          .then((result) => {
            if (!result || !result.tileUrl) return;
            const { tileUrl, bounds } = result;
            const doAdd = () => {
              add_image_layer(map, tileUrl, rasterId, true, bounds, false);
              pinHomepageAlwaysOnTop(layer.id);
            };
            if (map.loaded()) doAdd();
            else map.once('load', doAdd);
          })
          .catch(() => {
            loadedHomepageLayerIdsRef.current.delete(layer.id);
          });
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers, mapRef]);

  // Default to the first category (lowest sort order) once categories load
  useEffect(() => {
    if (categories.length > 0 && !activeCategory) {
      setActiveCategory(categories[0].key);
    }
  }, [categories, activeCategory]);

  // Load the first layer of the active category whenever category or layers change
  useEffect(() => {
    if (!layers.length || !activeCategory) return;

    // Match by hazard_category key first, then fall back to keyword inference —
    // but never silently fall back to layers[0] (that would show the wrong layer)
    const target = layers.find((l) => (l.hazard_category ?? inferCategory(l)) === activeCategory);
    if (!target) return;

    const map = mapRef?.current as any;
    if (!map) return;

    const cadence = target.dataset.cadence;
    const rasterId = `raster-home-${target.id}`;

    setLegendEntries(Object.entries(target.legend || {}));
    setCurrentDateLabel(null);

    const controller = new AbortController();

    // Remove the previous layer immediately so the map shows a clean state
    if (prevLayerIdRef.current) {
      remove_image_layer(map, `raster-home-${prevLayerIdRef.current}`);
      prevLayerIdRef.current = null;
    }

    fetchDatasetAvailability({ datasetId: target.dataset.id, cadence })
      .then(({ max, options }) => {
        if (controller.signal.aborted) return;
        const date = max || options[0]?.value;
        if (!date) return;
        setCurrentDateLabel(date);
        return fetchDatasetVisualization({ datasetId: target.dataset.id, cadence, date });
      })
      .then((result) => {
        if (controller.signal.aborted || !result || !result.tileUrl) return;
        prevLayerIdRef.current = target.id;
        const { tileUrl, bounds } = result;
        if (map.loaded()) {
          add_image_layer(map, tileUrl, rasterId, true, bounds, false);
          pinHomepageAlwaysOnTop();
        } else {
          map.once('load', () => {
            if (controller.signal.aborted) return;
            add_image_layer(map, tileUrl, rasterId, true, bounds, false);
            pinHomepageAlwaysOnTop();
          });
        }
      })
      .catch(() => {});

    return () => controller.abort();
  }, [activeCategory, layers, mapRef]);

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      {/* Hero — left panel (unchanged) + map + AI panel */}
      <section className="flex flex-col lg:flex-row" style={{ height: '50vh', minHeight: '420px' }}>
        {/* Left: text panel — UNCHANGED */}
        <div className="bg-hub-800 text-white flex flex-col justify-center px-10 py-14 lg:w-[480px] shrink-0">
          <h1 className="text-4xl font-bold leading-tight mb-4">Multi-Hazard Hub</h1>
          <p className="text-gray-300 text-base leading-relaxed mb-8">
            Monitoring, advisory, and geospatial data access for climate and
            hazard risks across Africa.
          </p>
          <div className="flex flex-wrap gap-3 mb-8">
            <Link
              to="/geoportal"
              className="flex items-center gap-2 bg-hub-400 hover:bg-hub-700 text-white px-5 py-2.5 rounded font-semibold text-sm transition-colors"
            >
              <Map className="size-4" />
              Open Geoportal
            </Link>
            <Link
              to="/data-services"
              className="flex items-center gap-2 border border-white text-white hover:bg-white/10 px-5 py-2.5 rounded font-semibold text-sm transition-colors"
            >
              <Database className="size-4" />
              Explore Data Services
            </Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'Drought', icon: <Droplets className="size-4" /> },
              { label: 'Weather Forecast', icon: <CloudRain className="size-4" /> },
              { label: 'Flood Risk', icon: <Waves className="size-4" /> },
            ].map(({ label, icon }) => (
              <Link
                key={label}
                to="/geoportal"
                className="flex items-center gap-1.5 border border-white/30 text-white/80 hover:border-hub-400 hover:text-hub-400 px-3 py-1.5 rounded text-xs transition-colors"
              >
                {icon}
                {label}
                <ArrowRight className="size-3" />
              </Link>
            ))}
          </div>
        </div>

        {/* Right: map + AI panel */}
        <div className="flex flex-1 min-w-0 min-h-[300px]">
          {/* Map */}
          <div className="flex-1 relative min-w-0">
            <MapComponent />

            {/* Category switcher buttons */}
            <div className="absolute top-3 left-3 z-10 flex gap-2 flex-wrap">
              {categories.slice(0, 4).map((cat) => (
                <button
                  key={cat.key}
                  onClick={() => setActiveCategory(cat.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium shadow transition-colors backdrop-blur-sm ${
                    activeCategory === cat.key
                      ? 'bg-hub-400 text-white'
                      : 'bg-white/90 text-gray-700 hover:bg-white'
                  }`}
                >
                  {cat.icon}
                  {cat.label}
                </button>
              ))}
            </div>

            {/* Legend overlay */}
            {legendEntries.length > 0 && (
              <div className="absolute bottom-8 right-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-md px-3 py-2.5 max-w-[180px]">
                <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Legend</p>
                <LegendDisplay entries={legendEntries} />
              </div>
            )}

            {/* Date label overlay */}
            {currentDateLabel && (
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 bg-hub-800/80 backdrop-blur-sm text-white text-xs font-medium px-3 py-1.5 rounded-full shadow">
                <CalendarDays className="size-3.5" />
                Latest: {currentDateLabel}
              </div>
            )}
          </div>

          {/* AI Analytics panel */}
          <AIAnalyticsPanel legendEntries={legendEntries} />
        </div>
      </section>

      {/* Explore the Hub */}
      <section className="py-12 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-hub-800 mb-1">Explore the Hub</h2>
          <div className="w-12 h-1 bg-hub-400 mb-8 rounded" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {exploreCards.map((card) => (
              <Link
                key={card.title}
                to={card.to}
                className="border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-hub-400 transition-all group"
              >
                <div className="mb-3">{card.icon}</div>
                <h3 className="font-bold text-gray-800 mb-1 group-hover:text-hub-700">{card.title}</h3>
                <p className="text-sm text-gray-500 mb-3">{card.description}</p>
                <ArrowRight className="size-4 text-hub-400" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Latest Updates */}
      <section className="py-12 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-2xl font-bold text-hub-800">Latest Updates</h2>
            <Link to="/bulletins" className="flex items-center gap-1 text-hub-400 hover:text-hub-700 text-sm font-medium">
              View all bulletins <ArrowRight className="size-4" />
            </Link>
          </div>
          <div className="w-12 h-1 bg-hub-400 mb-8 rounded" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {mockBulletins.map((b) => (
              <div key={b.title} className="bg-white border border-gray-200 rounded-lg p-5 flex gap-4">
                <div className="shrink-0 mt-0.5">{b.icon}</div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-800 mb-1 leading-snug">{b.title}</p>
                  <p className="text-xs text-gray-400 mb-2">Issued on {b.issued}</p>
                  <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded ${b.categoryColor}`}>
                    {b.category}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Partners footer */}
      <footer className="bg-white border-t border-gray-200 py-6 px-6">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-6 flex-wrap">
            <span className="text-xs text-gray-400 font-medium uppercase tracking-wide">Our Partners</span>
            {partners.map((p) => (
              <span key={p} className="text-sm font-semibold text-gray-500 border border-gray-200 px-3 py-1 rounded">{p}</span>
            ))}
          </div>
          <p className="text-xs text-gray-400">© 2026 ACMAD &nbsp;|&nbsp; Last updated: 26 May 2026</p>
        </div>
      </footer>
    </div>
  );
}
