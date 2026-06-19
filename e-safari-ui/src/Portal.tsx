import { useEffect, useRef, useState } from 'react';
import Map from './components/map';
import { DataPanel } from './components/DataPanel';
import { LayerControls } from './components/LayerControls';
import { MobileDrawer } from './components/MobileDrawer';
import { GeocodingControl } from '@maptiler/geocoding-control/react';
import { createMapLibreGlMapController } from '@maptiler/geocoding-control/maplibregl-controller';
import maplibregl from 'maplibre-gl';
import '@maptiler/geocoding-control/style.css';
import { Menu } from 'lucide-react';
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
  const [opacity, setOpacity] = useState<number>(85);
  const [mapController, setMapController] = useState<ReturnType<typeof createMapLibreGlMapController>>();
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<CountryOption | null>(null);
  const [layerSelectionOptions, setLayerSelectionOptions] = useState<
    Record<string, Partial<Record<SelectorKey, LayerSelectOption[]>>>
  >({});
  const [availabilityCache, setAvailabilityCache] = useState<
    Record<string, { available: string[]; max: string }>
  >({});
  const loadedRasterIdRef = useRef<string | null>(null);

  const {
    layers,
    loading,
    error,
    activeLayerId,
    activeLayer,
    setActiveLayerId,
    layerSelections,
    setLayerSelections,
  } = useCatalogLayers(language);

  const { mapRef } = useMap() ?? { mapRef: { current: null } };

  useEffect(() => {
    if (activeLayer) {
      setOpacity(activeLayer.ui?.opacity ?? 85);
    }
  }, [activeLayer?.id]);

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

  const handleOpacityChange = (value: number) => {
    setOpacity(value);
    const map = mapRef?.current;
    const rasterId = loadedRasterIdRef.current;
    if (map && rasterId && map.getLayer(rasterId)) {
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

  // Effect 1: Fetch availability when dataset/cadence changes
  useEffect(() => {
    if (!activeLayer || activeLayer.type !== 'raster') {
      return;
    }

    const cadence = activeLayer.dataset.cadence;
    const datasetId = activeLayer.dataset.id;
    const cacheKey = `${datasetId}-${cadence}`;

    // Skip if already cached
    if (availabilityCache[cacheKey]) {
      return;
    }

    fetchDatasetAvailability({ datasetId, cadence })
      .then((availability) => {
        const available = availability.options.map((option) => option.value);
        setAvailabilityCache((previous) => ({
          ...previous,
          [cacheKey]: { available, max: availability.max },
        }));

        // Set default selection if none exists
        const defaultSelection = defaultSelectionFromAvailability(
          cadence,
          available,
          availability.max,
        );

        setLayerSelections((previous) => {
          const current = previous[activeLayer.id] || {};
          if (buildVisualizationDate(cadence, current)) {
            return previous;
          }
          return {
            ...previous,
            [activeLayer.id]: { ...current, ...defaultSelection },
          };
        });
      })
      .catch(() => {
        // On error, set empty cache to allow retry
        setAvailabilityCache((previous) => ({
          ...previous,
          [cacheKey]: { available: [], max: '' },
        }));
      });
  }, [activeLayer?.id, activeLayer?.dataset.id, activeLayer?.dataset.cadence, setLayerSelections]);

  // Effect 2: Recompute options whenever active layer selection changes
  useEffect(() => {
    if (!activeLayer || activeLayer.type !== 'raster') {
      return;
    }

    const cadence = activeLayer.dataset.cadence;
    const datasetId = activeLayer.dataset.id;
    const cacheKey = `${datasetId}-${cadence}`;
    const cached = availabilityCache[cacheKey];

    if (!cached) {
      return;
    }

    const currentSelection = layerSelections[activeLayer.id] || {};
    const nextOptions: Partial<Record<SelectorKey, LayerSelectOption[]>> = {};

    activeLayer.selectors.forEach((selector) => {
      const fromApi = optionsFromAvailability(
        cached.available,
        selector.key,
        currentSelection,
        language,
      );
      nextOptions[selector.key] =
        fromApi.length > 0
          ? fromApi
          : getFallbackSelectorOptions(selector.key, language);
    });

    setLayerSelectionOptions((previous) => ({
      ...previous,
      [activeLayer.id]: nextOptions,
    }));
  }, [activeLayer?.id, activeLayer?.dataset.id, activeLayer?.dataset.cadence, activeLayer?.selectors, layerSelections, availabilityCache, language]);

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const map = mapRef?.current as any;
    if (!map) return;
    const init = () => setMapController(createMapLibreGlMapController(map, maplibregl));
    if (map.loaded()) init();
    else map.once('load', init);
  }, [mapRef?.current]);

  useEffect(() => {
    const map = mapRef?.current;
    if (!map) {
      return;
    }

    const applyRasterLayer = () => {
      const previousRasterId = loadedRasterIdRef.current;
      if (previousRasterId) {
        remove_image_layer(map, previousRasterId);
        loadedRasterIdRef.current = null;
      }

      if (!activeLayer || activeLayer.type !== 'raster') {
        useLegendStore.getState().clearLegends();
        return;
      }

      const cadence = activeLayer.dataset.cadence;
      const selection = layerSelections[activeLayer.id] || {};
      const vizDate = buildVisualizationDate(cadence, selection);
      if (!vizDate) {
        return;
      }

      const rasterLayerId = `raster-${activeLayer.id}`;

      fetchDatasetVisualization({
        datasetId: activeLayer.dataset.id,
        cadence,
        date: vizDate,
      })
        .then((payload) => {
          if (loadedRasterIdRef.current && loadedRasterIdRef.current !== rasterLayerId) {
            remove_image_layer(map, loadedRasterIdRef.current);
          }
          if (!payload.tileUrl) {
            return;
          }
          add_image_layer(map, payload.tileUrl, rasterLayerId, true, payload.bounds, true, opacity / 100);
          loadedRasterIdRef.current = rasterLayerId;

          useLegendStore.getState().clearLegends();
          const legendMap = activeLayer.legend;
          if (legendMap && Object.keys(legendMap).length > 0) {
            const legendNode = renderLegend(legendMap, activeLayer.title);
            addLegendOnce(legendNode, activeLayer.title);
          }
        })
        .catch(() => {
          remove_image_layer(map, rasterLayerId);
        });
    };

    if (map.isStyleLoaded()) {
      applyRasterLayer();
    } else {
      map.once('load', applyRasterLayer);
    }
  }, [activeLayer, layerSelections, mapRef]);

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
              activeLayerId={activeLayerId}
              onLayerChange={(layerId) => {
                setActiveLayerId(layerId);
                setRightBarTab('Legend');
              }}
              onLayerDeactivate={() => setActiveLayerId(null as any)}
              language={language}
              selectionValues={layerSelections}
              selectionOptions={layerSelectionOptions}
              onSelectionChange={handleSelectionChange}
              loading={loading}
              error={error}
              opacity={opacity}
              onOpacityChange={handleOpacityChange}
            />
          </div>
        </div>

        <div className="flex-1 min-h-0 relative">
          <Map />
          <RightBar
            activeLayer={activeLayer}
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
          activeLayerId={activeLayerId}
          onLayerChange={(layerId) => {
            setActiveLayerId(layerId);
            setRightBarTab('Legend');
          }}
          onLayerDeactivate={() => setActiveLayerId(null as any)}
          language={language}
          selectionValues={layerSelections}
          selectionOptions={layerSelectionOptions}
          onSelectionChange={handleSelectionChange}
          loading={loading}
          error={error}
          activeLayer={activeLayer}
          opacity={opacity}
          onOpacityChange={handleOpacityChange}
        />
      </div>
    </div>
  );
};

export default Portal;
