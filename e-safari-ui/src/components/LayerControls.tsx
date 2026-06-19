import { useEffect, useState } from 'react';
import Select from 'react-select';
import { ChevronRight, Info, Layers } from 'lucide-react';
import { Language } from '../types';
import { YearSlider } from './YearSlider';
import type {
  CatalogLayer,
  LayerSelectOption,
  LayerSelectionValue,
  SelectorConfig,
  SelectorKey,
} from '../types/catalogLayer';
import '../styles/layercontrol.css';

interface LayerControlsProps {
  layers: CatalogLayer[];
  activeLayerIds: string[];
  onLayerToggle: (layerId: string) => void;
  language: Language;
  selectionValues: Record<string, LayerSelectionValue>;
  selectionOptions: Record<string, Partial<Record<SelectorKey, LayerSelectOption[]>>>;
  onSelectionChange: (layerId: string, field: SelectorKey, value?: string) => void;
  loading?: boolean;
  error?: string | null;
  opacities: Record<string, number>;
  onOpacityChange: (layerId: string, value: number) => void;
}

const translations = {
  en: {
    title: 'Data Layers',
    loading: 'Loading layers…',
    empty: 'No layers published for this project.',
    error: 'Could not load layers',
    legend: 'Legend',
    resolution: 'Resolution',
    source: 'Source',
    coverage: 'Coverage',
    updateFrequency: 'Updated',
    methodology: 'Methodology',
    opacity: 'Layer opacity',
    close: 'Close',
  },
  fr: {
    title: 'Couches de Données',
    loading: 'Chargement des couches…',
    empty: 'Aucune couche publiée pour ce projet.',
    error: 'Impossible de charger les couches',
    legend: 'Légende',
    resolution: 'Résolution',
    source: 'Source',
    coverage: 'Couverture',
    updateFrequency: 'Mise à jour',
    methodology: 'Méthodologie',
    opacity: 'Opacité',
    close: 'Fermer',
  },
};

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-1" style={{ fontSize: '11px' }}>
      <span className="text-green-700 font-medium">{label}: </span>
      <span className="text-gray-600">{value}</span>
    </div>
  );
}

export function LayerControls({
  layers,
  activeLayerIds,
  onLayerToggle,
  language,
  selectionValues,
  selectionOptions,
  onSelectionChange,
  loading,
  error,
  opacities,
  onOpacityChange,
}: LayerControlsProps) {
  const t = translations[language];
  const [infoLayerId, setInfoLayerId] = useState<string | null>(null);

  // Auto-select the first available option for any selector that has no current value.
  // Fires when options load OR when the active layer set changes.
  useEffect(() => {
    layers.forEach((layer) => {
      layer.selectors.forEach((field) => {
        const options = selectionOptions[layer.id]?.[field.key];
        if (!options?.length) return;
        const current = selectionValues[layer.id]?.[field.key];
        if (!current) {
          onSelectionChange(layer.id, field.key, options[0].value);
        }
      });
    });
  // selectionValues intentionally omitted — the !current guard prevents loops
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectionOptions, activeLayerIds, layers]);

  const isFieldEnabled = (selection: LayerSelectionValue, field: SelectorConfig) => {
    if (!field.dependsOn || field.dependsOn.length === 0) return true;
    return field.dependsOn.every((dep) => Boolean(selection[dep]));
  };

  const titleRow = (
    <div className="flex items-center gap-2 mb-3">
      <Layers className="size-4 text-gray-500" />
      <h2>{t.title}</h2>
    </div>
  );

  if (loading) return <div className="p-4">{titleRow}<p className="text-sm text-gray-500">{t.loading}</p></div>;
  if (error)   return <div className="p-4">{titleRow}<p className="text-sm text-red-600">{t.error}</p></div>;
  if (!layers.length) return <div className="p-4">{titleRow}<p className="text-sm text-gray-500">{t.empty}</p></div>;

  return (
    <div className="p-4">
      {titleRow}
      <div className="space-y-1.5">
        {layers.map((layer) => {
          const isActive = activeLayerIds.includes(layer.id);
          const showInfo = infoLayerId === layer.id;

          return (
            <div
              key={layer.id}
              className={isActive ? 'rounded-xl border border-green-200 bg-white shadow-sm overflow-hidden' : ''}
            >
              {/* Layer row */}
              <div className={`flex items-center gap-2 px-3 ${isActive ? 'py-2.5 bg-green-50' : 'py-2 border-b border-gray-100'}`}>
                {/* Icon */}
                <div className="size-6 shrink-0 flex items-center justify-center">
                  {layer.icon?.url ? (
                    <img src={layer.icon.url} alt="" className="size-6 object-contain" />
                  ) : null}
                </div>

                {/* Name */}
                <span
                  className={`flex-1 min-w-0 truncate ${isActive ? 'font-semibold text-green-800' : 'text-gray-700'}`}
                  style={{ fontSize: '12px' }}
                >
                  {layer.labels.title[language]}
                </span>

                {/* Info button */}
                <button
                  type="button"
                  aria-label="Info"
                  onClick={(e) => {
                    e.stopPropagation();
                    setInfoLayerId((c) => (c === layer.id ? null : layer.id));
                  }}
                  className={`shrink-0 size-5 rounded-full border flex items-center justify-center transition-colors ${
                    showInfo
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-gray-300 text-gray-400 hover:bg-gray-100'
                  }`}
                >
                  <Info className="size-3" />
                </button>

                {/* Toggle switch */}
                <button
                  type="button"
                  role="switch"
                  aria-label={layer.labels.title[language]}
                  aria-checked={isActive}
                  onClick={(e) => {
                    e.stopPropagation();
                    onLayerToggle(layer.id);
                  }}
                  className="relative inline-flex h-4 w-8 items-center rounded-full transition-colors shrink-0 focus:outline-none"
                  style={{ backgroundColor: isActive ? '#16803d' : '#d1d5db' }}
                >
                  <span
                    className={`inline-block h-3 w-3 transform rounded-full bg-white shadow transition-transform ${
                      isActive ? 'translate-x-[18px]' : 'translate-x-[2px]'
                    }`}
                  />
                </button>

                {/* Chevron — hidden when active to keep layout consistent */}
                <ChevronRight className={`size-3.5 shrink-0 ${isActive ? 'invisible' : 'text-gray-300'}`} />
              </div>

              {/* Selectors (active only) */}
              {isActive && layer.selectors.length > 0 && (
                <div className="px-3 pb-2 pt-2" onClick={(e) => e.stopPropagation()}>
                  <div className="flex flex-wrap items-end gap-2">
                    {layer.selectors.map((field) => {
                      const selection = selectionValues[layer.id] || {};
                      const options = selectionOptions[layer.id]?.[field.key] || [];
                      const selectedOption = options.find((o) => o.value === selection[field.key]) || null;
                      // Fall back to first option so the label always reflects what the map renders.
                      const displayOption = selectedOption ?? options[0] ?? null;
                      const enabled = isFieldEnabled(selection, field);

                      if (layer.dataset.cadence === 'annual' && field.key === 'year') {
                        const yearDisplay = selection.year ?? options[0]?.value;
                        return (
                          <div key={`${layer.id}-${field.key}`} style={{ width: '100%' }}>
                            <p className="mb-1 text-gray-600" style={{ fontSize: '11px' }}>
                              {field.label[language]}{yearDisplay ? `: ${yearDisplay}` : ''}
                            </p>
                            <YearSlider
                              options={options}
                              value={selection.year}
                              onChange={(year) => onSelectionChange(layer.id, 'year', year)}
                            />
                          </div>
                        );
                      }

                      return (
                        <div key={`${layer.id}-${field.key}`} style={{ width: 120 }}>
                          <p className="mb-1 text-gray-600" style={{ fontSize: '11px' }}>
                            {field.label[language]}{displayOption ? `: ${displayOption.label}` : ''}
                          </p>
                          <Select
                            className="layer-select"
                            classNamePrefix="layer-select-controls"
                            options={options}
                            value={null}
                            isClearable={!field.required}
                            isDisabled={!enabled}
                            placeholder={language === 'fr' ? 'Sélectionner..' : 'Select..'}
                            onChange={(option) => onSelectionChange(layer.id, field.key, option?.value)}
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Opacity slider (active only) */}
              {isActive && (
                <div className="px-3 pb-3" onClick={(e) => e.stopPropagation()}>
                  <div className="border-t border-gray-100 pt-2" style={{ maxWidth: '85%' }}>
                    <div className="flex justify-between text-green-700 mb-1.5" style={{ fontSize: '11px' }}>
                      <span>{t.opacity}</span>
                      <span>{Math.round(opacities[layer.id] ?? layer.ui?.opacity ?? 85)}%</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={opacities[layer.id] ?? 85}
                      onChange={(e) => onOpacityChange(layer.id, Number(e.target.value))}
                      className="layer-slider"
                    />
                  </div>
                </div>
              )}

              {/* Info panel */}
              {showInfo && (
                <div className="border-t border-green-100 bg-green-50 px-3 py-2.5">
                  <p className="font-semibold text-green-700 mb-1" style={{ fontSize: '12px' }}>
                    {layer.labels.title[language]}
                  </p>
                  {layer.description?.plain && (
                    <p className="text-gray-600 mb-2" style={{ fontSize: '11px' }}>
                      {layer.description.plain}
                    </p>
                  )}
                  {layer.details?.legend_description && (
                    <MetaRow label={t.legend} value={layer.details.legend_description} />
                  )}
                  {layer.details?.coverage && (
                    <MetaRow label={t.coverage} value={layer.details.coverage} />
                  )}
                  {layer.details?.resolution && (
                    <MetaRow label={t.resolution} value={layer.details.resolution} />
                  )}
                  {layer.details?.update_frequency && (
                    <MetaRow label={t.updateFrequency} value={layer.details.update_frequency} />
                  )}
                  {layer.details?.source_organization && (
                    <MetaRow label={t.source} value={layer.details.source_organization} />
                  )}
                  {layer.details?.methodology_url && (
                    <a
                      href={layer.details.methodology_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block mt-1 text-green-700 underline hover:text-green-900"
                      style={{ fontSize: '11px' }}
                    >
                      {t.methodology} ↗
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => setInfoLayerId(null)}
                    style={{
                      marginTop: '10px',
                      display: 'block',
                      marginLeft: 'auto',
                      padding: '4px 14px',
                      borderRadius: '6px',
                      border: '1.5px solid #16803d',
                      color: '#16803d',
                      fontWeight: '600',
                      fontSize: '11px',
                      backgroundColor: 'white',
                      cursor: 'pointer',
                    }}
                  >
                    {t.close}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
