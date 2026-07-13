import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Map from './components/map';
import { DataPanel } from './components/DataPanel';
import { LayerControls } from './components/LayerControls';
import { MobileDrawer } from './components/MobileDrawer';
import { GeocodingControl } from '@maptiler/geocoding-control/react';
import { createMapLibreGlMapController } from '@maptiler/geocoding-control/maplibregl-controller';
import maplibregl from 'maplibre-gl';
import '@maptiler/geocoding-control/style.css';
import { Locate, Menu } from 'lucide-react';
import { Button } from './components/ui/button';
import { Language } from './types';
import RightBar from './components/RightBar';
import { add_image_layer, remove_image_layer } from './components/Maputils.js';
import { useMap } from './components/MapContext.jsx';
import { useCatalogLayers } from './hooks/useCatalogLayers';
import { buildVisualizationDate } from './lib/cadenceSelectors';
import {
  defaultSelectionFromAvailability,
  optionsFromAvailability,
} from './lib/availabilitySelectors';
import {
  fetchDatasetAvailability,
  fetchDatasetVisualization,
  getFallbackSelectorOptions,
} from './services/layersApi';
import type { BoundsObject } from './services/layersApi';
import type { LayerSelectOption, LayerSelectionValue, SelectorKey } from './types/catalogLayer';
import { addLegendOnce, renderLegend } from './components/LegendUtils';
import { useLegendStore } from './components/stores/useLegendStore';
import { SubHeader } from './components/SubHeader';
import type { CountryOption } from './components/SubHeader';

export interface SelectedFeature {
  type: string;
  data: unknown;
  id: string;
}

type PortalProps = {
  language: Language;
};

const Portal = ({ language }: PortalProps) => {
  const [rightBarTab, setRightBarTab] = useState<'Legend' | 'Analysis'>('Legend');
  const [showMobilePanel, setShowMobilePanel] = useState(false);
  const [selectedFeature] = useState<SelectedFeature | null>(null);
  const [opacities, setOpacities] = useState<Record<string, number>>({});
  const [mapController, setMapController] = useState<ReturnType<typeof createMapLibreGlMapController>>();
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<CountryOption | null>(null);
  const [layerSelectionOptions, setLayerSelectionOptions] = useState<
    Record<string, Partial<Record<SelectorKey, LayerSelectOption[]>>>
  >({});
  const [availabilityCache, setAvailabilityCache] = useState<
    Record<string, { available: string[]; max: string }>
  >({});
  const loadedRasterIdsRef = useRef<Record<string, string>>({});
  // Tracks which vizDate is currently rendered for each layer — skip re-fetch when unchanged.
  const loadedVizDatesRef = useRef<Record<string, string>>({});
  // Flips true after the very first auto-zoom; never resets so only one auto-zoom ever occurs
  const hasInitialZoomedRef = useRef<boolean>(false);
  const [layerBounds, setLayerBounds] = useState<Record<string, BoundsObject | null>>({});
  const [searchParams] = useSearchParams();
  const preselectLayerId = searchParams.get('layer') ?? undefined;

  const {
    layers,
    loading,
    error,
    activeLayerIds,
    activeLayers,
    toggleActiveLayer,
    layerSelections,
    setLayerSelections,
  } = useCatalogLayers(language, preselectLayerId);

  const { mapRef } = useMap() ?? { mapRef: { current: null } };

  // The legend store is a module-level singleton that outlives this component's mount
  // (e.g. Home -> Geoportal -> Home -> Geoportal with a different layer), so without this
  // a legend added during a previous visit lingers even though its raster is long gone.
  useEffect(() => {
    useLegendStore.getState().clearLegends();
  }, []);

  useEffect(() => {
    fetch('/api/catalog/projects/e-safari/countries/')
      .then((r) => r.json())
      .then((data: CountryOption[]) => setCountries(data))
      .catch(() => {});
  }, []);

  const handleCountryChange = (country: CountryOption | null) => {
    setSelectedCountry(country);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const map = mapRef?.current as any;
    if (!country || !map) return;
    const { west, south, east, north } = country.bounds;
    map.fitBounds([[west, south], [east, north]], { padding: 40 });
  };

  const handleOpacityChange = (layerId: string, value: number) => {
    setOpacities((prev) => ({ ...prev, [layerId]: value }));
    const map = mapRef?.current;
    const rasterId = `raster-${layerId}`;
    if (map && map.getLayer(rasterId)) {
      map.setPaintProperty(rasterId, 'raster-opacity', value / 100);
    }
  };

  const handleSelectionChange = (layerId: string, field: SelectorKey, value?: string) => {
    const layerConfig = layers.find((item) => item.id === layerId);
    const selectors = layerConfig?.selectors || [];

    setLayerSelections((previous) => {
      const currentLayerSelection = previous[layerId] || {};
      const nextLayerSelection: LayerSelectionValue = {
        ...currentLayerSelection,
        [field]: value,
      };

      selectors.forEach((selector) => {
        if (selector.dependsOn?.includes(field)) {
          delete nextLayerSelection[selector.key];
        }
      });

      return {
        ...previous,
        [layerId]: nextLayerSelection,
      };
    });
  };

  // Effect 1: Fetch availability for each active layer not yet cached
  useEffect(() => {
    activeLayers.forEach((layer) => {
      if (layer.type !== 'raster') return;
      const cadence = layer.dataset.cadence;
      const datasetId = layer.dataset.id;
      const cacheKey = `${datasetId}-${cadence}`;
      if (availabilityCache[cacheKey]) return;

      fetchDatasetAvailability({ datasetId, cadence })
        .then((availability) => {
          const available = availability.options.map((option) => option.value);
          setAvailabilityCache((previous) => ({
            ...previous,
            [cacheKey]: { available, max: availability.max ?? '' },
          }));
          const defaultSelection = defaultSelectionFromAvailability(cadence, available, availability.max);
          setLayerSelections((previous) => {
            const current = previous[layer.id] || {};
            if (buildVisualizationDate(cadence, current)) return previous;
            return { ...previous, [layer.id]: { ...current, ...defaultSelection } };
          });
        })
        .catch(() => {
          setAvailabilityCache((previous) => ({
            ...previous,
            [cacheKey]: { available: [], max: '' },
          }));
        });
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayerIds, layers, availabilityCache]);

  // Effect 2: Recompute selector options for all active layers
  useEffect(() => {
    activeLayers.forEach((layer) => {
      if (layer.type !== 'raster') return;
      const cacheKey = `${layer.dataset.id}-${layer.dataset.cadence}`;
      const cached = availabilityCache[cacheKey];
      if (!cached) return;

      const currentSelection = layerSelections[layer.id] || {};
      const nextOptions: Partial<Record<SelectorKey, LayerSelectOption[]>> = {};

      layer.selectors.forEach((selector) => {
        const fromApi = optionsFromAvailability(cached.available, selector.key, currentSelection, language);
        nextOptions[selector.key] =
          fromApi.length > 0 ? fromApi : getFallbackSelectorOptions(selector.key, language);
      });

      setLayerSelectionOptions((previous) => ({ ...previous, [layer.id]: nextOptions }));
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayerIds, layers, availabilityCache, layerSelections, language]);

  useEffect(() => {
    let cancelled = false;

    const initWhenReady = () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const map = mapRef?.current as any;
      if (!map) {
        if (!cancelled) window.setTimeout(initWhenReady, 50);
        return;
      }

      const init = () => {
        if (!cancelled) {
          setMapController(createMapLibreGlMapController(map, maplibregl));
        }
      };

      if (map.loaded()) init();
      else map.once('load', init);
    };

    initWhenReady();
    return () => {
      cancelled = true;
    };
  }, [mapRef]);

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const map = mapRef?.current as any;
    if (!map) return;

    let cancelled = false;

    const applyRasterLayers = () => {
      // Remove rasters whose layers are no longer active
      Object.entries(loadedRasterIdsRef.current).forEach(([layerId, rasterId]) => {
        if (!activeLayerIds.includes(layerId)) {
          remove_image_layer(map, rasterId);
          delete loadedRasterIdsRef.current[layerId];
          delete loadedVizDatesRef.current[layerId];
          const title = layers.find((l) => l.id === layerId)?.title;
          if (title) useLegendStore.getState().removeLegendByTitle(title);
        }
      });

      // Add/refresh each active raster layer
      activeLayers.forEach((layer) => {
        if (layer.type !== 'raster') return;
        const cadence = layer.dataset.cadence;
        const selection = layerSelections[layer.id] || {};
        const vizDate = buildVisualizationDate(cadence, selection);
        if (!vizDate) return;

        const rasterId = `raster-${layer.id}`;

        // Already rendered with this date and still present on the map — skip to preserve layer stacking order.
        if (
          loadedVizDatesRef.current[layer.id] === vizDate &&
          map.getLayer(rasterId)
        ) return;
        fetchDatasetVisualization({ datasetId: layer.dataset.id, cadence, date: vizDate })
          .then((payload) => {
            // Discard stale responses: layer may have been toggled off or the
            // selection/date may have changed since this request was issued.
            if (cancelled) return;
            if (!activeLayerIds.includes(layer.id)) return;
            const currentSelection = layerSelections[layer.id] || {};
            if (buildVisualizationDate(cadence, currentSelection) !== vizDate) return;
            if (!payload.tileUrl) return;
            // Remove stale tile for this layer before adding the refreshed one
            if (map.getSource(rasterId)) remove_image_layer(map, rasterId);
            add_image_layer(map, payload.tileUrl, rasterId, true, payload.bounds, false, (opacities[layer.id] ?? layer.ui?.opacity ?? 85) / 100);
            loadedRasterIdsRef.current[layer.id] = rasterId;
            loadedVizDatesRef.current[layer.id] = vizDate;
            // Store bounds for the zoom button
            setLayerBounds((prev) => ({ ...prev, [layer.id]: payload.bounds }));
            // Auto-zoom once ever on first layer load
            if (!hasInitialZoomedRef.current && payload.bounds) {
              const { minx, miny, maxx, maxy } = payload.bounds;
              map.fitBounds([[minx, miny], [maxx, maxy]], { padding: 40 });
              hasInitialZoomedRef.current = true;
            }
            const legendMap = layer.legend;
            if (legendMap && Object.keys(legendMap).length > 0) {
              addLegendOnce(renderLegend(legendMap, layer.title), layer.title);
            }
          })
          .catch(() => {
            if (!cancelled) remove_image_layer(map, rasterId);
          });
      });
    };

    if (map.isStyleLoaded()) {
      applyRasterLayers();
    } else {
      map.once('load', applyRasterLayers);
      return () => {
        map.off('load', applyRasterLayers);
      };
    }

    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayerIds, activeLayers, layerSelections, mapRef]);

  const handleZoomToLayers = () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const map = mapRef?.current as any;
    if (!map || activeLayerIds.length === 0) return;
    const bounds = activeLayerIds.map((id) => layerBounds[id]).filter(Boolean) as BoundsObject[];
    if (bounds.length === 0) return;
    const minx = Math.min(...bounds.map((b) => b.minx));
    const miny = Math.min(...bounds.map((b) => b.miny));
    const maxx = Math.max(...bounds.map((b) => b.maxx));
    const maxy = Math.max(...bounds.map((b) => b.maxy));
    map.fitBounds([[minx, miny], [maxx, maxy]], { padding: 40 });
  };

  return (
    <div className="h-full min-h-0 overflow-hidden flex flex-col bg-gray-50">
      <SubHeader
        countries={countries}
        selectedCountry={selectedCountry}
        onCountryChange={handleCountryChange}
        language={language}
      />
      <div className="flex-1 flex overflow-hidden relative">
        <div className="hidden lg:flex lg:w-80 flex-col border-r bg-white overflow-hidden">
          <div className="geocoding border-b flex-shrink-0">
            <GeocodingControl
              apiKey={import.meta.env.VITE_MAPTILER_KEY}
              mapController={mapController}
              language={language}
              bbox={
                selectedCountry
                  ? [
                      selectedCountry.bounds.west,
                      selectedCountry.bounds.south,
                      selectedCountry.bounds.east,
                      selectedCountry.bounds.north,
                    ]
                  : undefined
              }
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            <LayerControls
              layers={layers}
              activeLayerIds={activeLayerIds}
              onLayerToggle={(layerId: string) => {
                toggleActiveLayer(layerId);
                setRightBarTab('Legend');
                // Seed opacity from layer config if not yet set
                const layer = layers.find((l) => l.id === layerId);
                if (layer) setOpacities((prev) => ({ [layerId]: layer.ui?.opacity ?? 85, ...prev }));
              }}
              language={language}
              selectionValues={layerSelections}
              selectionOptions={layerSelectionOptions}
              onSelectionChange={handleSelectionChange}
              loading={loading}
              error={error}
              opacities={opacities}
              onOpacityChange={handleOpacityChange}
            />
          </div>
        </div>

        <div className="flex-1 min-h-0 relative">
          <Map />
          {activeLayerIds.length > 0 && (
            <button
              type="button"
              title={language === 'fr' ? 'Zoom sur la couche' : 'Zoom to layer'}
              aria-label={language === 'fr' ? 'Zoom sur la couche' : 'Zoom to layer'}
              onClick={handleZoomToLayers}
              style={{
                position: 'absolute',
                top: 115,
                right: 20,
                zIndex: 1000,
                width: 29,
                height: 29,
                backgroundColor: 'white',
                border: 'none',
                borderRadius: '4px',
                boxShadow: '0 0 0 2px rgba(0,0,0,.1)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Locate style={{ width: 15, height: 15, color: '#374151' }} />
            </button>
          )}
          <RightBar
            activeLayer={activeLayers[0] ?? null}
            language={language}
            selectedFeature={selectedFeature}
            activeTab={rightBarTab}
            onTabChange={setRightBarTab}
          />

          <Button
            className="lg:hidden absolute bottom-4 left-4 z-[1000] shadow-lg"
            size="lg"
            onClick={() => setShowMobilePanel(true)}
          >
            <Menu className="size-5 mr-2" />
            {language === 'en' ? 'Controls' : 'Contrôles'}
          </Button>
        </div>

        <MobileDrawer
          isOpen={showMobilePanel}
          onClose={() => setShowMobilePanel(false)}
          layers={layers}
          activeLayerIds={activeLayerIds}
          onLayerToggle={(layerId: string) => {
            toggleActiveLayer(layerId);
            setRightBarTab('Legend');
            const layer = layers.find((l) => l.id === layerId);
            if (layer) setOpacities((prev) => ({ [layerId]: layer.ui?.opacity ?? 85, ...prev }));
          }}
          language={language}
          selectionValues={layerSelections}
          selectionOptions={layerSelectionOptions}
          onSelectionChange={handleSelectionChange}
          loading={loading}
          error={error}
          activeLayer={activeLayers[0] ?? null}
          opacities={opacities}
          onOpacityChange={handleOpacityChange}
        />
      </div>
    </div>
  );
};

export default Portal;
