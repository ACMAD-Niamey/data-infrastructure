import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Layers, Search, ChevronDown, ChevronUp,
  Info, X, ChevronLeft, ChevronRight,
  Map as MapIcon, Filter, ExternalLink,
  Download, Copy, Globe, Crosshair,
} from 'lucide-react';
import { useHazardCategories } from '../hooks/useHazardCategories';
import type { HazardCategory } from '../hooks/useHazardCategories';
import {
  Dialog, DialogContent, DialogTitle,
} from '../components/ui/dialog';
import NavBar from '../components/NavBar';
import MapComponent from '../components/map.jsx';
import { useMap } from '../components/MapContext.jsx';
import { add_image_layer, remove_image_layer } from '../components/Maputils.js';
import { LegendDisplay } from '../components/LegendDisplay';
import { useCatalogLayers } from '../hooks/useCatalogLayers';
import {
  fetchDatasetAvailability,
  fetchDatasetVisualization,
} from '../services/layersApi';
import type { CatalogLayer } from '../types/catalogLayer';
import type { BoundsObject } from '../services/layersApi';
import { inferCategory } from '../lib/inferCategory';

// ---------------------------------------------------------------------------
// Hazard categories — loaded from backend, fallback to hardcoded list
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Right panel
// ---------------------------------------------------------------------------

type RightPanelProps = {
  layer: CatalogLayer;
  isActive: boolean;
  onClose: () => void;
  onToggle: (layer: CatalogLayer) => void;
  onOpacityChange: (layerId: string, opacity: number) => void;
  opacityMap: Record<string, number>;
  categories: HazardCategory[];
  onTileApplied: (layerId: string) => void;
};

function RightPanel({ layer, isActive, onClose, onToggle, onOpacityChange, opacityMap, categories, onTileApplied }: RightPanelProps) {
  const [tab, setTab] = useState<'details' | 'analysis'>('details');
  const [showFullDetails, setShowFullDetails] = useState(false);
  const [availability, setAvailability] = useState<string[]>([]);
  const [maxDate, setMaxDate] = useState<string | null>(null);
  const [vizDate, setVizDate] = useState<string | null>(null);
  const [dateIndex, setDateIndex] = useState(0);
  const [availError, setAvailError] = useState(false);
  const { mapRef } = useMap() ?? { mapRef: { current: null } };

  const cadence = layer.dataset.cadence;

  // Load availability when the layer changes
  useEffect(() => {
    setAvailability([]);
    setVizDate(null);
    setAvailError(false);
    fetchDatasetAvailability({ datasetId: layer.dataset.id, cadence })
      .then(({ options, max }) => {
        const dates = options.map((o) => o.value);
        setAvailability(dates);
        setMaxDate(max);
        setVizDate(max || dates[0] || null);
        setDateIndex(0);
      })
      .catch(() => setAvailError(true));
  }, [layer.dataset.id, cadence]);

  // Fetch and add the tile when the selected date changes — only when layer is active
  useEffect(() => {
    if (!isActive || !vizDate) return;
    const map = mapRef?.current;
    if (!map) return;

    const rasterId = `raster-${layer.id}`;
    const controller = new AbortController();

    fetchDatasetVisualization({ datasetId: layer.dataset.id, cadence, date: vizDate })
      .then(({ tileUrl, bounds }) => {
        if (controller.signal.aborted || !tileUrl) return;
        add_image_layer(map, tileUrl, rasterId, true, bounds, false);
        onTileApplied(layer.id);
      })
      .catch(() => {});

    return () => controller.abort();
  // onTileApplied intentionally omitted — it's a stable per-render closure from the parent,
  // including it would refire this effect every render without changing what it does here.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive, layer.id, layer.dataset.id, cadence, vizDate, mapRef]);

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
    setVizDate(availability[next]);
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
    <div className="flex flex-col">
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

      <div className="p-4 space-y-5">
        {tab === 'details' ? (
          <>
            {/* Title */}
            <div>
              <h3 className="font-bold text-gray-800 text-base leading-snug">{layer.title}</h3>
              {layer.description?.plain && (
                <p className="text-xs text-gray-500 mt-0.5">{layer.description.plain}</p>
              )}
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
                <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">
                  Legend
                  {layer.details?.legend_description && (
                    <span className="normal-case font-normal text-[11px] text-gray-400"> — {layer.details.legend_description}</span>
                  )}
                </p>
                <LegendDisplay entries={Object.entries(layer.legend)} />
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
                    ['Source', layer.details?.source_organization || layer.dataset.title],
                    ['Cadence', layer.dataset.cadence],
                    ['Dataset Type', layer.dataset.dataset_type],
                    ['Coverage', layer.details?.coverage || 'Africa'],
                  ].map(([k, v]) => (
                    <tr key={k}>
                      <td className="py-1.5 text-gray-500 pr-4 whitespace-nowrap">{k}</td>
                      <td className="py-1.5 text-gray-700 font-medium">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              onClick={() => setShowFullDetails(true)}
              className="w-full flex items-center justify-center gap-2 border border-hub-400 text-hub-700 hover:bg-hub-100 rounded px-4 py-2 text-sm font-medium transition-colors"
            >
              View Full Details <ExternalLink className="size-3.5" />
            </button>

            <FullDetailsDialog
              open={showFullDetails}
              onClose={() => setShowFullDetails(false)}
              layer={layer}
              isActive={isActive}
              onToggle={onToggle}
              categories={categories}
              availability={availability}
              dateIndex={dateIndex}
              currentDateLabel={currentDateLabel}
              onDateNav={handleDateNav}
            />
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
// Full details dialog
// ---------------------------------------------------------------------------

const DETAIL_TABS = ['Overview', 'Metadata', 'Legend', 'Time Range', 'Access', 'Methodology'] as const;
type DetailTab = typeof DETAIL_TABS[number];

type FullDetailsDialogProps = {
  open: boolean;
  onClose: () => void;
  layer: CatalogLayer;
  isActive: boolean;
  onToggle: (layer: CatalogLayer) => void;
  categories: HazardCategory[];
  availability: string[];
  dateIndex: number;
  currentDateLabel: string;
  onDateNav: (dir: -1 | 1) => void;
};

function FullDetailsDialog({
  open, onClose, layer, isActive, onToggle, categories,
  availability, dateIndex, currentDateLabel, onDateNav,
}: FullDetailsDialogProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>('Overview');
  const categoryKey = inferCategory(layer);
  const hazardCat = categories.find((c) => c.key === categoryKey);

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

  const d = layer.details;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-lg w-full max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
        {/* Header */}
        <div className="px-5 pt-5 pb-3 border-b border-gray-100">
          <div className="flex items-start justify-between gap-3 pr-6">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <DialogTitle className="text-base font-bold text-gray-800 leading-snug">
                  {layer.title}
                </DialogTitle>
                {isActive && (
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 bg-hub-400 text-white rounded">
                    Active
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500">{layer.dataset.title}</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-0 mt-3 -mb-px overflow-x-auto">
            {DETAIL_TABS.map((t) => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={`text-xs font-medium px-3 py-2 border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === t
                    ? 'border-hub-400 text-hub-700'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {activeTab === 'Overview' && (
            <div className="space-y-5">
              {/* Description */}
              <p className="text-sm text-gray-700 leading-relaxed">
                {layer.description?.plain || 'No description available.'}
              </p>

              {/* Metadata + Legend side by side */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Metadata</p>
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-gray-100">
                      {[
                        ['Category',   hazardCat?.label ?? '—'],
                        ['Latest',     availability[0] ?? '—'],
                        ['Coverage',   d?.coverage || 'Africa'],
                        ['Resolution', d?.resolution || '—'],
                        ['Update',     d?.update_frequency || '—'],
                        ['Source',     d?.source_organization || layer.dataset.title],
                      ].map(([k, v]) => (
                        <tr key={k}>
                          <td className="py-1.5 text-gray-500 pr-3 whitespace-nowrap">{k}</td>
                          <td className="py-1.5 text-gray-800 font-medium">{v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Legend
                    {d?.legend_description && (
                      <span className="normal-case font-normal text-[11px] text-gray-400"> — {d.legend_description}</span>
                    )}
                  </p>
                  {layer.legend && Object.keys(layer.legend).length > 0 ? (
                    <div className="space-y-1.5">
                      {Object.entries(layer.legend).map(([label, color]) => (
                        <div key={label} className="flex items-center gap-2">
                          <div className="w-4 h-4 rounded-full border border-gray-200 shrink-0"
                               style={{ backgroundColor: color as string }} />
                          <span className="text-xs text-gray-700">{label}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400">No legend defined.</p>
                  )}
                </div>
              </div>

              {/* Time Range */}
              {availability.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Time Range</p>
                  <div className="flex items-center gap-3 border border-gray-200 rounded px-3 py-2">
                    <button onClick={() => onDateNav(1)} disabled={dateIndex >= availability.length - 1}
                            className="text-gray-400 hover:text-gray-700 disabled:opacity-30" title="Older">
                      <ChevronLeft className="size-4" />
                    </button>
                    <span className="flex-1 text-center text-sm font-medium text-gray-700">{currentDateLabel}</span>
                    <button onClick={() => onDateNav(-1)} disabled={dateIndex <= 0}
                            className="text-gray-400 hover:text-gray-700 disabled:opacity-30" title="Newer">
                      <ChevronRight className="size-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* Access */}
              <div className="space-y-2">
                <button onClick={() => onToggle(layer)}
                        className={`w-full flex items-center justify-center gap-2 rounded px-4 py-2 text-sm font-medium transition-colors ${
                          isActive ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' : 'bg-hub-800 text-white hover:bg-hub-700'
                        }`}>
                  <Layers className="size-4" />
                  {isActive ? 'Remove from Map' : 'Add to Map'}
                </button>
                <div className="flex gap-2">
                  <button className="flex-1 flex items-center justify-center gap-1.5 border border-gray-300 text-gray-700 hover:border-hub-400 rounded px-3 py-2 text-sm font-medium">
                    <Download className="size-4" /> Download
                  </button>
                  <button className="flex-1 flex items-center justify-center gap-1.5 border border-gray-300 text-gray-700 hover:border-hub-400 rounded px-3 py-2 text-sm font-medium">
                    <Copy className="size-4" /> Copy API Link
                  </button>
                </div>
                {hazardCat?.external_system_url && (
                  <a href={hazardCat.external_system_url} target="_blank" rel="noopener noreferrer"
                     className="w-full flex items-center justify-center gap-2 bg-hub-100 text-hub-800 hover:bg-hub-400 hover:text-white rounded px-4 py-2 text-sm font-semibold transition-colors">
                    <Globe className="size-4" />
                    Go to {hazardCat.external_system_name || hazardCat.label} System
                    <ExternalLink className="size-3.5" />
                  </a>
                )}
              </div>

              {/* Methodology snippet */}
              {d?.methodology_html && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Methodology</p>
                  <div className="text-sm text-gray-700 leading-relaxed line-clamp-4 prose prose-sm max-w-none"
                       dangerouslySetInnerHTML={{ __html: d.methodology_html }} />
                  {d.methodology_url && (
                    <a href={d.methodology_url} target="_blank" rel="noopener noreferrer"
                       className="inline-flex items-center gap-1 mt-2 text-xs font-medium text-hub-700 hover:text-hub-400">
                      View full methodology documentation <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'Metadata' && (
            <table className="w-full text-sm">
              <tbody className="divide-y divide-gray-100">
                {[
                  ['Category',   hazardCat?.label ?? '—'],
                  ['Latest',     availability[0] ?? '—'],
                  ['Coverage',   d?.coverage || 'Africa'],
                  ['Resolution', d?.resolution || '—'],
                  ['Update',     d?.update_frequency || '—'],
                  ['Source',     d?.source_organization || layer.dataset.title],
                ].map(([k, v]) => (
                  <tr key={k}>
                    <td className="py-2 text-gray-500 pr-6 whitespace-nowrap w-28">{k}</td>
                    <td className="py-2 text-gray-800 font-medium">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === 'Legend' && (
            layer.legend && Object.keys(layer.legend).length > 0 ? (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Legend
                  {d?.legend_description && (
                    <span className="normal-case font-normal text-[11px] text-gray-400"> — {d.legend_description}</span>
                  )}
                </p>
                <div className="space-y-2">
                  {Object.entries(layer.legend).map(([label, color]) => (
                    <div key={label} className="flex items-center gap-3">
                      <div
                        className="w-5 h-5 rounded border border-gray-300 shrink-0"
                        style={{ backgroundColor: color as string }}
                      />
                      <span className="text-sm text-gray-700">{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No legend defined for this layer.</p>
            )
          )}

          {activeTab === 'Time Range' && (
            <div>
              {availability.length > 0 ? (
                <>
                  {/* Date navigator */}
                  <div className="flex items-center gap-3 border border-gray-200 rounded px-3 py-2">
                    <button
                      onClick={() => onDateNav(1)}
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
                      onClick={() => onDateNav(-1)}
                      disabled={dateIndex <= 0}
                      className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
                      title="Newer"
                    >
                      <ChevronRight className="size-4" />
                    </button>
                  </div>

                  {/* Timeline range */}
                  <div className="mt-5">
                    {/* Track with cursor dot */}
                    <div className="relative h-1.5 bg-gray-200 rounded-full mx-1">
                      <div
                        className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-hub-400 rounded-full shadow border-2 border-white transition-all duration-150"
                        style={{
                          left: `calc(${((availability.length - 1 - dateIndex) / Math.max(availability.length - 1, 1)) * 100}% - 6px)`,
                        }}
                      />
                    </div>
                    {/* Start / end labels */}
                    <div className="flex justify-between mt-2">
                      <div className="text-left">
                        <p className="text-[10px] text-gray-400 uppercase tracking-wide">Start</p>
                        <p className="text-xs font-medium text-gray-600">{availability[availability.length - 1]}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[10px] text-gray-400 uppercase tracking-wide">End</p>
                        <p className="text-xs font-medium text-gray-600">{availability[0]}</p>
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-gray-400 mt-3 text-center">
                    {availability.length} available dates
                  </p>
                </>
              ) : (
                <p className="text-sm text-gray-400">No time range data available.</p>
              )}
            </div>
          )}

          {activeTab === 'Access' && (
            <div className="space-y-3">
              <button
                onClick={() => onToggle(layer)}
                className={`w-full flex items-center justify-center gap-2 rounded px-4 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    : 'bg-hub-800 text-white hover:bg-hub-700'
                }`}
              >
                <Layers className="size-4" />
                {isActive ? 'Remove from Map' : 'Add to Map'}
              </button>
              <button className="w-full flex items-center justify-center gap-2 border border-gray-300 text-gray-700 hover:border-hub-400 hover:text-hub-700 rounded px-4 py-2.5 text-sm font-medium transition-colors">
                <Download className="size-4" /> Download
              </button>
              <button className="w-full flex items-center justify-center gap-2 border border-gray-300 text-gray-700 hover:border-hub-400 hover:text-hub-700 rounded px-4 py-2.5 text-sm font-medium transition-colors">
                <Copy className="size-4" /> Copy API Link
              </button>
              {hazardCat?.external_system_url && (
                <a
                  href={hazardCat.external_system_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center gap-2 bg-hub-100 text-hub-800 hover:bg-hub-400 hover:text-white rounded px-4 py-2.5 text-sm font-semibold transition-colors"
                >
                  <Globe className="size-4" />
                  Go to {hazardCat.external_system_name || hazardCat.label} System
                  <ExternalLink className="size-3.5" />
                </a>
              )}
            </div>
          )}

          {activeTab === 'Methodology' && (
            <div>
              {d?.methodology_html ? (
                <div
                  className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: d.methodology_html }}
                />
              ) : (
                <p className="text-sm text-gray-400">No methodology description added yet.</p>
              )}
              {d?.methodology_url && (
                <a
                  href={d.methodology_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 mt-4 text-sm font-medium text-hub-700 hover:text-hub-400"
                >
                  View full methodology documentation <ExternalLink className="size-3.5" />
                </a>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Layer card inside accordion
// ---------------------------------------------------------------------------

type LayerCardProps = {
  layer: CatalogLayer;
  isActive: boolean;
  onToggle: (layer: CatalogLayer) => void;
};

function LayerCard({ layer, isActive, onToggle }: LayerCardProps) {
  // Info/View Layer/Full Details all just ensure the layer is active — that's what
  // makes its details card appear in the stacked right panel. Only the pill can turn it off.
  const activate = () => {
    if (!isActive) onToggle(layer);
  };

  return (
    <div className={`rounded-lg border p-3 mb-2 transition-all ${isActive ? 'border-hub-400 bg-hub-100/40' : 'border-gray-200 bg-white'}`}>
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
              onClick={activate}
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
          onClick={activate}
          className="flex items-center gap-1.5 bg-hub-800 hover:bg-hub-700 text-white text-xs font-medium px-3 py-1.5 rounded transition-colors"
        >
          <Layers className="size-3" />
          View Layer
        </button>
        <button
          onClick={activate}
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
  const [searchParams] = useSearchParams();
  const [activeCategory, setActiveCategory] = useState<string>('drought');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['drought']));
  // Ordered newest-first: toggling a layer on prepends its id, so the stacked
  // details panel below can render `activeLayerIds` in order to get "newest on top" for free.
  const [activeLayerIds, setActiveLayerIds] = useState<string[]>([]);
  const [opacityMap, setOpacityMap] = useState<Record<string, number>>({});
  const [boundsMap, setBoundsMap] = useState<Record<string, BoundsObject>>({});
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

  // Re-assert any active always-on-top layer (e.g. an admin-boundary overlay) above the
  // map's other raster layers. Call this right after any *other* layer's tile is added,
  // since MapLibre renders layers in the order they were last added/moved.
  const pinAlwaysOnTopLayers = (justAppliedLayerId: string) => {
    const map = mapRef?.current as any;
    if (!map) return;
    layers.forEach((l) => {
      if (l.id === justAppliedLayerId || !l.ui?.always_on_top) return;
      if (!activeLayerIds.includes(l.id)) return;
      const rasterId = `raster-${l.id}`;
      if (map.getLayer(rasterId)) map.moveLayer(rasterId);
    });
  };

  // Fetch the latest tile for a layer and add it to the map
  const loadLayerTile = async (layer: CatalogLayer) => {
    const map = mapRef?.current as any;
    if (!map) return;
    const cadence = layer.dataset.cadence;
    try {
      const { options, max } = await fetchDatasetAvailability({ datasetId: layer.dataset.id, cadence });
      const dates = options.map((o) => o.value);
      // Use max directly — avoids cadence-specific key mismatches in buildVisualizationDate
      const vizDate = max || dates[0] || null;
      if (!vizDate) return;
      const { tileUrl, bounds } = await fetchDatasetVisualization({ datasetId: layer.dataset.id, cadence, date: vizDate });
      if (!tileUrl) return;
      const rasterId = `raster-${layer.id}`;
      const opacity = (opacityMap[layer.id] ?? layer.ui.opacity ?? 85) / 100;

      const doAdd = () => {
        add_image_layer(map, tileUrl, rasterId, true, bounds, false);
        if (bounds) setBoundsMap((prev) => ({ ...prev, [layer.id]: bounds }));
        if (map.getLayer(rasterId)) {
          map.setPaintProperty(rasterId, 'raster-opacity', opacity);
        }
        pinAlwaysOnTopLayers(layer.id);
      };

      // Defer until the map style is loaded — addSource/addLayer throw if called too early
      if (map.loaded()) {
        doAdd();
      } else {
        map.once('load', doAdd);
      }
    } catch (err) {
      console.error('[loadLayerTile] failed:', err);
    }
  };

  // Seed activeLayerIds from ui.default_visible once, the first time layers finish loading —
  // so a layer marked default-visible in the CMS comes up toggled on and rendered, unprompted.
  const hasSeededDefaultsRef = useRef(false);
  useEffect(() => {
    if (hasSeededDefaultsRef.current || loading || layers.length === 0) return;
    hasSeededDefaultsRef.current = true;
    const defaults = layers.filter((l) => l.ui?.default_visible);
    if (defaults.length === 0) return;
    setActiveLayerIds((prev) => [
      ...defaults.map((l) => l.id).filter((id) => !prev.includes(id)),
      ...prev,
    ]);
    defaults.forEach((layer) => loadLayerTile(layer));
  }, [layers, loading]);

  const handleToggle = (layer: CatalogLayer) => {
    const isCurrentlyActive = activeLayerIds.includes(layer.id);
    setActiveLayerIds((prev) =>
      isCurrentlyActive ? prev.filter((id) => id !== layer.id) : [layer.id, ...prev],
    );
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

  // Deep-link support: ?dataset=<dataset_id> (e.g. from the Data Platforms detail
  // page, or a homepage category shortcut) opens that specific dataset — expands
  // its category and activates it on the map — once layers have loaded.
  const hasAppliedDatasetParamRef = useRef(false);
  useEffect(() => {
    if (hasAppliedDatasetParamRef.current || loading || layers.length === 0) return;
    const datasetParam = searchParams.get('dataset');
    if (!datasetParam) return;
    const target = layers.find((l) => l.dataset.id === datasetParam);
    if (!target) return;
    hasAppliedDatasetParamRef.current = true;

    const category = inferCategory(target);
    setActiveCategory(category);
    setExpandedCategories((prev) => new Set(prev).add(category));
    setActiveLayerIds((prev) => (prev.includes(target.id) ? prev : [target.id, ...prev]));
    loadLayerTile(target);
  }, [layers, loading, searchParams]);

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
                              isActive={activeLayerIds.includes(layer.id)}
                              onToggle={handleToggle}
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

          {/* Zoom to layer — appears below the north arrow when the topmost active layer has bounds */}
          {activeLayerIds[0] && boundsMap[activeLayerIds[0]] && (
            <button
              onClick={() => {
                const b = boundsMap[activeLayerIds[0]];
                const map = mapRef?.current as any;
                if (map && b) map.fitBounds([[b.minx, b.miny], [b.maxx, b.maxy]], { padding: 40, duration: 800 });
              }}
              title="Zoom to layer"
              className="absolute top-[128px] right-3 z-10 bg-white rounded shadow p-1.5 hover:bg-gray-50 text-gray-600 hover:text-hub-700 transition-colors"
            >
              <Crosshair className="size-4" />
            </button>
          )}
        </div>

        {/* Right panel — stacked details for every active layer, newest on top, one scroll region */}
        {activeLayerIds.length > 0 && (
          <div className="w-80 bg-white border-l border-gray-200 flex flex-col overflow-hidden shrink-0">
            <div className="flex-1 overflow-y-auto divide-y divide-gray-200">
              {activeLayerIds.map((id) => {
                const layer = layers.find((l) => l.id === id);
                if (!layer) return null;
                return (
                  <RightPanel
                    key={id}
                    layer={layer}
                    isActive
                    onClose={() => handleToggle(layer)}
                    onToggle={handleToggle}
                    onOpacityChange={handleOpacityChange}
                    opacityMap={opacityMap}
                    categories={categories}
                    onTileApplied={pinAlwaysOnTopLayers}
                  />
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
