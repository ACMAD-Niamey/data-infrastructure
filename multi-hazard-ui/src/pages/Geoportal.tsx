import { useEffect, useState } from 'react';
import {
  Layers, Search, ChevronDown, ChevronUp,
  Info, X, ChevronLeft, ChevronRight,
  Map as MapIcon, Filter, ExternalLink,
} from 'lucide-react';
import { useHazardCategories } from '../hooks/useHazardCategories';
import type { HazardCategory } from '../hooks/useHazardCategories';
import NavBar from '../components/NavBar';
import MapComponent from '../components/map.jsx';
import { useMap } from '../components/MapContext.jsx';
import { add_image_layer, remove_image_layer } from '../components/Maputils.js';
import { useCatalogLayers } from '../hooks/useCatalogLayers';
import {
  fetchDatasetAvailability,
  fetchDatasetVisualization,
} from '../services/layersApi';
import {
  defaultSelectionFromAvailability,
} from '../lib/availabilitySelectors';
import { buildVisualizationDate } from '../lib/cadenceSelectors';
import type { CatalogLayer, LayerSelectionValue } from '../types/catalogLayer';

// ---------------------------------------------------------------------------
// Hazard categories — loaded from backend, fallback to hardcoded list
// ---------------------------------------------------------------------------

// Fallback: assign category from layer title keywords when hazard_category not set
function inferCategory(layer: CatalogLayer): string {
  const t = layer.title.toLowerCase();
  if (layer.hazard_category) return layer.hazard_category;
  if (t.includes('drought') || t.includes('soil moisture') || t.includes('sma') || t.includes('cdi') || t.includes('spi')) return 'drought';
  if (t.includes('flood') || t.includes('river')) return 'flood';
  if (t.includes('rain') || t.includes('weather') || t.includes('precipitation') || t.includes('forecast')) return 'weather';
  if (t.includes('heat') || t.includes('temperature') || t.includes('lst')) return 'heat';
  if (t.includes('vegetation') || t.includes('ndvi') || t.includes('crop') || t.includes('agriculture')) return 'agriculture';
  if (t.includes('boundary') || t.includes('admin') || t.includes('country')) return 'boundary';
  return 'other';
}

// ---------------------------------------------------------------------------
// Right panel
// ---------------------------------------------------------------------------

type RightPanelProps = {
  layer: CatalogLayer;
  isActive: boolean;
  onClose: () => void;
  onOpacityChange: (layerId: string, opacity: number) => void;
  opacityMap: Record<string, number>;
  categories: HazardCategory[];
};

function RightPanel({ layer, isActive, onClose, onOpacityChange, opacityMap, categories }: RightPanelProps) {
  const [tab, setTab] = useState<'details' | 'analysis'>('details');
  const [availability, setAvailability] = useState<string[]>([]);
  const [maxDate, setMaxDate] = useState<string | null>(null);
  const [selection, setSelection] = useState<LayerSelectionValue>({});
  const [dateIndex, setDateIndex] = useState(0);
  const [availError, setAvailError] = useState(false);
  const { mapRef } = useMap() ?? { mapRef: { current: null } };

  const cadence = layer.dataset.cadence;

  // Load availability when the layer changes
  useEffect(() => {
    setAvailability([]);
    setAvailError(false);
    fetchDatasetAvailability({ datasetId: layer.dataset.id, cadence })
      .then(({ options, max }) => {
        const dates = options.map((o) => o.value);
        setAvailability(dates);
        setMaxDate(max);
        setSelection(defaultSelectionFromAvailability(cadence, dates, max));
        setDateIndex(0);
      })
      .catch(() => setAvailError(true));
  }, [layer.dataset.id, cadence]);

  // Fetch and add the tile when the selected date changes — only when layer is active
  useEffect(() => {
    if (!isActive) return;
    const map = mapRef?.current;
    if (!map) return;
    const vizDate = buildVisualizationDate(cadence, selection);
    if (!vizDate) return;

    const rasterId = `raster-${layer.id}`;
    const controller = new AbortController();

    fetchDatasetVisualization({ datasetId: layer.dataset.id, cadence, date: vizDate })
      .then(({ tileUrl, bounds }) => {
        if (controller.signal.aborted || !tileUrl) return;
        add_image_layer(map, tileUrl, rasterId, true, bounds, false);
      })
      .catch(() => {});

    return () => controller.abort();
  }, [isActive, layer.id, layer.dataset.id, cadence, selection, mapRef]);

  // Apply opacity changes without re-fetching the tile
  useEffect(() => {
    const map = mapRef?.current;
    if (!map) return;
    const rasterId = `raster-${layer.id}`;
    if (!map.getLayer(rasterId)) return;
    const opacity = (opacityMap[layer.id] ?? layer.ui.opacity ?? 85) / 100;
    map.setPaintProperty(rasterId, 'raster-opacity', opacity);
  }, [layer.id, layer.ui.opacity, opacityMap, mapRef]);

  const handleDateNav = (dir: -1 | 1) => {
    const next = dateIndex + dir;
    if (next < 0 || next >= availability.length) return;
    setDateIndex(next);
    const date = availability[next];
    setSelection(defaultSelectionFromAvailability(cadence, [date], date));
  };

  const currentDateLabel = availability[dateIndex] ?? (maxDate ?? '—');
  const opacity = opacityMap[layer.id] ?? layer.ui.opacity ?? 85;
  const categoryKey = inferCategory(layer);
  const category = categories.find((c) => c.key === categoryKey);

  const badgeColors: Record<string, string> = {
    drought: 'bg-amber-100 text-amber-700',
    flood: 'bg-blue-100 text-blue-700',
    weather: 'bg-sky-100 text-sky-700',
    heat: 'bg-red-100 text-red-700',
    agriculture: 'bg-green-100 text-green-700',
    exposure: 'bg-purple-100 text-purple-700',
    impact: 'bg-orange-100 text-orange-700',
    boundary: 'bg-gray-100 text-gray-700',
    other: 'bg-gray-100 text-gray-600',
  };

  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col overflow-hidden shrink-0">
      {/* Tabs */}
      <div className="flex items-center border-b border-gray-200">
        <button
          onClick={() => setTab('details')}
          className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
            tab === 'details' ? 'border-hub-400 text-hub-700' : 'border-transparent text-gray-500'
          }`}
        >
          Layer Details
        </button>
        <button
          onClick={() => setTab('analysis')}
          className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
            tab === 'analysis' ? 'border-hub-400 text-hub-700' : 'border-transparent text-gray-500'
          }`}
        >
          Analysis
        </button>
        <button onClick={onClose} className="px-3 py-3 text-gray-400 hover:text-gray-700">
          <X className="size-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {tab === 'details' ? (
          <>
            {/* Title */}
            <div>
              <h3 className="font-bold text-gray-800 text-base leading-snug">{layer.title}</h3>
              <p className="text-xs text-gray-500 mt-0.5">{layer.dataset.title}</p>
              {category && (
                <span className={`inline-block mt-2 text-xs font-medium px-2 py-0.5 rounded ${badgeColors[categoryKey] ?? 'bg-gray-100 text-gray-600'}`}>
                  {category.label}
                </span>
              )}
            </div>

            {/* Date navigator — dates are sorted newest-first; left=older, right=newer */}
            {availability.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-1 font-medium uppercase tracking-wide">Date</p>
                <div className="flex items-center gap-2 border border-gray-200 rounded px-2 py-1.5">
                  <button
                    onClick={() => handleDateNav(1)}
                    disabled={dateIndex >= availability.length - 1}
                    className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                    title="Older"
                  >
                    <ChevronLeft className="size-4" />
                  </button>
                  <span className="flex-1 text-center text-sm font-medium text-gray-700">
                    {currentDateLabel}
                  </span>
                  <button
                    onClick={() => handleDateNav(-1)}
                    disabled={dateIndex <= 0}
                    className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                    title="Newer"
                  >
                    <ChevronRight className="size-4" />
                  </button>
                </div>
              </div>
            )}
            {availError && (
              <p className="text-xs text-red-500">Could not load date availability.</p>
            )}

            {/* Legend */}
            {layer.legend && Object.keys(layer.legend).length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">Legend</p>
                <div className="space-y-1.5">
                  {Object.entries(layer.legend).map(([label, color]) => (
                    <div key={label} className="flex items-center gap-2">
                      <div
                        className="size-4 rounded-full border border-gray-300 shrink-0"
                        style={{ backgroundColor: color as string }}
                      />
                      <span className="text-xs text-gray-700">{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Opacity */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Opacity</p>
                <span className="text-xs font-semibold text-gray-700">{opacity}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={opacity}
                onChange={(e) => onOpacityChange(layer.id, Number(e.target.value))}
                className="w-full accent-hub-400"
              />
            </div>

            {/* Metadata */}
            <div>
              <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">Metadata</p>
              <table className="w-full text-xs">
                <tbody className="divide-y divide-gray-100">
                  {[
                    ['Source', layer.dataset.title],
                    ['Cadence', layer.dataset.cadence],
                    ['Dataset Type', layer.dataset.dataset_type],
                    ['Coverage', 'Africa'],
                  ].map(([k, v]) => (
                    <tr key={k}>
                      <td className="py-1.5 text-gray-500 pr-4 whitespace-nowrap">{k}</td>
                      <td className="py-1.5 text-gray-700 font-medium">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button className="w-full flex items-center justify-center gap-2 border border-hub-400 text-hub-700 hover:bg-hub-100 rounded px-4 py-2 text-sm font-medium transition-colors">
              View Full Details <ExternalLink className="size-3.5" />
            </button>
          </>
        ) : (
          <div className="flex items-center justify-center h-32 text-gray-400 text-sm">
            Analysis coming soon
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Layer card inside accordion
// ---------------------------------------------------------------------------

type LayerCardProps = {
  layer: CatalogLayer;
  isActive: boolean;
  isSelected: boolean;
  onToggle: (layer: CatalogLayer) => void;
  onSelect: (layer: CatalogLayer) => void;
};

function LayerCard({ layer, isActive, isSelected, onToggle, onSelect }: LayerCardProps) {
  return (
    <div className={`rounded-lg border p-3 mb-2 transition-all ${isSelected ? 'border-hub-400 bg-hub-100/40' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-start gap-2">
        {/* Pill toggle */}
        <button
          onClick={() => onToggle(layer)}
          className={`shrink-0 w-11 h-6 rounded-full transition-colors relative ${isActive ? 'bg-hub-400' : 'bg-gray-300'}`}
          aria-label={isActive ? 'Disable layer' : 'Enable layer'}
        >
          <span
            className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm transition-all duration-200 ${isActive ? 'right-1' : 'left-1'}`}
          />
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-1">
            <span className="text-sm font-semibold text-gray-800 leading-snug">{layer.title}</span>
            <button
              onClick={() => onSelect(layer)}
              className="text-gray-400 hover:text-gray-700 shrink-0"
              title="Layer details"
            >
              <Info className="size-3.5" />
            </button>
          </div>
          {layer.description?.plain && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{layer.description.plain}</p>
          )}
        </div>
      </div>

      <div className="flex gap-2 mt-2.5">
        <button
          onClick={() => {
            // Always activate (never deactivate) — use the pill toggle to turn off
            if (!isActive) onToggle(layer);
            onSelect(layer);
          }}
          className="flex items-center gap-1.5 bg-hub-800 hover:bg-hub-700 text-white text-xs font-medium px-3 py-1.5 rounded transition-colors"
        >
          <Layers className="size-3" />
          View Layer
        </button>
        <button
          onClick={() => onSelect(layer)}
          className="text-xs font-medium border border-gray-300 hover:border-hub-400 text-gray-600 hover:text-hub-700 px-3 py-1.5 rounded transition-colors"
        >
          Full Details
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Geoportal page
// ---------------------------------------------------------------------------

export default function Geoportal() {
  const [activeCategory, setActiveCategory] = useState<string>('drought');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['drought']));
  const [activeLayerIds, setActiveLayerIds] = useState<Set<string>>(new Set());
  const [selectedLayer, setSelectedLayer] = useState<CatalogLayer | null>(null);
  const [opacityMap, setOpacityMap] = useState<Record<string, number>>({});
  const [showDatasets, setShowDatasets] = useState(true);
  const [search, setSearch] = useState('');

  const { mapRef } = useMap() ?? { mapRef: { current: null } };
  const { layers, loading, error: layersError, reload } = useCatalogLayers('en');
  const categories = useHazardCategories();

  // Group layers by inferred category
  const layersByCategory: Record<string, CatalogLayer[]> = {};
  for (const layer of layers) {
    const cat = inferCategory(layer);
    if (!layersByCategory[cat]) layersByCategory[cat] = [];
    layersByCategory[cat].push(layer);
  }

  const filteredLayers = (cat: string) => {
    const list = layersByCategory[cat] ?? [];
    if (!search) return list;
    return list.filter((l) => l.title.toLowerCase().includes(search.toLowerCase()));
  };

  const handleCategoryClick = (key: string) => {
    setActiveCategory(key);
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Fetch the latest tile for a layer and add it to the map
  const loadLayerTile = async (layer: CatalogLayer) => {
    const map = mapRef?.current;
    if (!map) return;
    const cadence = layer.dataset.cadence;
    try {
      const { options, max } = await fetchDatasetAvailability({ datasetId: layer.dataset.id, cadence });
      const dates = options.map((o) => o.value);
      const def = defaultSelectionFromAvailability(cadence, dates, max);
      const vizDate = buildVisualizationDate(cadence, def);
      if (!vizDate) return;
      const { tileUrl, bounds } = await fetchDatasetVisualization({ datasetId: layer.dataset.id, cadence, date: vizDate });
      if (!tileUrl) return;
      const rasterId = `raster-${layer.id}`;
      add_image_layer(map, tileUrl, rasterId, true, bounds, false);
      const opacity = (opacityMap[layer.id] ?? layer.ui.opacity ?? 85) / 100;
      map.setPaintProperty(rasterId, 'raster-opacity', opacity);
    } catch {}
  };

  const handleToggle = (layer: CatalogLayer) => {
    const isCurrentlyActive = activeLayerIds.has(layer.id);
    setActiveLayerIds((prev) => {
      const next = new Set(prev);
      if (isCurrentlyActive) next.delete(layer.id);
      else next.add(layer.id);
      return next;
    });
    if (isCurrentlyActive) {
      const map = mapRef?.current;
      if (map) remove_image_layer(map, `raster-${layer.id}`);
    } else {
      loadLayerTile(layer);
    }
  };

  const handleOpacityChange = (layerId: string, opacity: number) => {
    setOpacityMap((prev) => ({ ...prev, [layerId]: opacity }));
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <NavBar />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Hazard icon strip */}
        <div className="w-[70px] bg-white border-r border-gray-200 flex flex-col items-center py-3 gap-1 overflow-y-auto shrink-0">
          {categories.map((cat) => (
            <button
              key={cat.key}
              onClick={() => handleCategoryClick(cat.key)}
              title={cat.label}
              className={`w-full flex flex-col items-center gap-1 py-2.5 px-1 transition-colors rounded-none ${
                activeCategory === cat.key
                  ? 'bg-hub-800 text-white'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              {cat.icon}
              <span className="text-[10px] font-medium text-center leading-tight">{cat.label}</span>
            </button>
          ))}
        </div>

        {/* Datasets panel */}
        {showDatasets && (
          <div className="w-[300px] bg-white border-r border-gray-200 flex flex-col overflow-hidden shrink-0">
            <div className="p-3 border-b border-gray-100">
              <h2 className="font-bold text-gray-800 text-base mb-2">Datasets</h2>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search datasets..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-7 pr-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:border-hub-400"
                  />
                </div>
                <button className="flex items-center gap-1 border border-gray-200 text-gray-600 text-xs px-2.5 py-1.5 rounded hover:border-hub-400">
                  All <ChevronDown className="size-3" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {loading && (
                <p className="text-sm text-gray-400 text-center py-6">Loading datasets…</p>
              )}
              {layersError && (
                <div className="p-4 text-center">
                  <p className="text-sm text-red-500 mb-2">{layersError}</p>
                  <button
                    onClick={reload}
                    className="text-xs font-medium border border-hub-400 text-hub-700 px-3 py-1.5 rounded hover:bg-hub-100"
                  >
                    Retry
                  </button>
                </div>
              )}
              {!loading && !layersError && categories.map((cat) => {
                const catLayers = filteredLayers(cat.key);
                if (catLayers.length === 0 && search) return null;
                const expanded = expandedCategories.has(cat.key);
                return (
                  <div key={cat.key} className="mb-1">
                    <button
                      onClick={() => handleCategoryClick(cat.key)}
                      className="w-full flex items-center justify-between px-2 py-2 hover:bg-gray-50 rounded"
                    >
                      <div className="flex items-center gap-2 text-sm font-bold text-gray-700 uppercase tracking-wide">
                        {cat.icon}
                        {cat.label}
                      </div>
                      {expanded ? <ChevronUp className="size-4 text-gray-400" /> : <ChevronDown className="size-4 text-gray-400" />}
                    </button>

                    {expanded && (
                      <div className="px-1 pb-1">
                        {catLayers.length === 0 ? (
                          <p className="text-xs text-gray-400 px-2 py-3 text-center">No datasets in this category</p>
                        ) : (
                          catLayers.map((layer) => (
                            <LayerCard
                              key={layer.id}
                              layer={layer}
                              isActive={activeLayerIds.has(layer.id)}
                              isSelected={selectedLayer?.id === layer.id}
                              onToggle={handleToggle}
                              onSelect={setSelectedLayer}
                            />
                          ))
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Map */}
        <div className="flex-1 relative min-w-0">
          <MapComponent />

          {/* Top toolbar */}
          <div className="absolute top-3 right-14 z-10 flex items-center gap-1 bg-white rounded-full shadow px-1 py-1">
            <button className="flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-hub-700 px-3 py-1.5 rounded-full hover:bg-gray-100 transition-colors">
              <Filter className="size-3.5" /> Filters
            </button>
            <div className="w-px h-4 bg-gray-200" />
            <button className="flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-hub-700 px-3 py-1.5 rounded-full hover:bg-gray-100 transition-colors">
              <MapIcon className="size-3.5" /> Map Styles
            </button>
            <div className="w-px h-4 bg-gray-200" />
            <button
              onClick={() => setShowDatasets((v) => !v)}
              className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full transition-colors ${
                showDatasets ? 'bg-hub-800 text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Layers className="size-3.5" /> Layers
            </button>
          </div>
        </div>

        {/* Right panel */}
        {selectedLayer && (
          <RightPanel
            layer={selectedLayer}
            isActive={activeLayerIds.has(selectedLayer.id)}
            onClose={() => setSelectedLayer(null)}
            onOpacityChange={handleOpacityChange}
            opacityMap={opacityMap}
            categories={categories}
          />
        )}
      </div>
    </div>
  );
}
