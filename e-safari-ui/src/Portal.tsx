import { useEffect, useRef, useState } from 'react';
import Map from './components/map';
import { DataPanel } from './components/DataPanel';
import { LayerControls } from './components/LayerControls';
import { MobileDrawer } from './components/MobileDrawer';
import { SearchBar } from './components/SearchBar';
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
  const [selectedFeature, setSelectedFeature] = useState<SelectedFeature | null>(null);
  const [mapCenter, setMapCenter] = useState<[number, number] | null>(null);
  const [layerSelectionOptions, setLayerSelectionOptions] = useState<
    Record<string, Partial<Record<SelectorKey, LayerSelectOption[]>>>
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

  const handleLocationSelect = (location: { name: string; coords: [number, number] }) => {
    setMapCenter(location.coords);
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

  useEffect(() => {
    if (!activeLayer || activeLayer.type !== 'raster') {
      return;
    }

    const cadence = activeLayer.dataset.cadence;
    const datasetId = activeLayer.dataset.id;
    fetchDatasetAvailability({ datasetId, cadence })
      .then((availability) => {
        const available = availability.options.map((option) => option.value);

        const nextOptions: Partial<Record<SelectorKey, LayerSelectOption[]>> = {};
        activeLayer.selectors.forEach((selector) => {
          const fromApi = optionsFromAvailability(
            available,
            selector.key,
            layerSelections[activeLayer.id] || {},
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
        const fallback: Partial<Record<SelectorKey, LayerSelectOption[]>> = {};
        activeLayer.selectors.forEach((selector) => {
          fallback[selector.key] = getFallbackSelectorOptions(selector.key, language);
        });
        setLayerSelectionOptions((previous) => ({
          ...previous,
          [activeLayer.id]: fallback,
        }));
      });
  }, [activeLayer?.id, activeLayer?.dataset.id, activeLayer?.dataset.cadence, language, setLayerSelections]);

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
          add_image_layer(map, payload.tileUrl, rasterLayerId, true, payload.bounds, true);
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
      <div className="flex-1 flex overflow-hidden relative">
        <div className="hidden lg:flex lg:w-96 flex-col border-r bg-white overflow-hidden">
          <div className="p-4 border-b flex-shrink-0">
            <SearchBar language={language} onLocationSelect={handleLocationSelect} />
          </div>
          <div className="flex-1 overflow-y-auto">
            <LayerControls
              layers={layers}
              activeLayerId={activeLayerId}
              onLayerChange={(layerId) => {
                setActiveLayerId(layerId);
                setRightBarTab('Legend');
              }}
              language={language}
              selectionValues={layerSelections}
              selectionOptions={layerSelectionOptions}
              onSelectionChange={handleSelectionChange}
              loading={loading}
              error={error}
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
          language={language}
          selectionValues={layerSelections}
          selectionOptions={layerSelectionOptions}
          onSelectionChange={handleSelectionChange}
          loading={loading}
          error={error}
          activeLayer={activeLayer}
        />
      </div>
    </div>
  );
};

export default Portal;
