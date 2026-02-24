import { useEffect, useState } from 'react';
import Map from './components/map';
import { DataPanel } from './components/DataPanel';
import { LayerControls } from './components/LayerControls';
import { MobileDrawer } from './components/MobileDrawer';
import { SearchBar } from './components/SearchBar';
import { Menu } from 'lucide-react';
import { Button } from './components/ui/button';
import { Language } from './types';
import RightBar from './components/RightBar';
import { DataLayer, layerRegistry, LayerSelectionValue, LayerSelectOption, SelectorKey } from './components/layers/layerRegistry';
import { fetchSelectorOptions, getFallbackSelectorOptions } from './services/layersApi';

export interface SelectedFeature {
  type: string;
  data: any;
  id: string;
}

type PortalProps = {
  language: Language;
};

const Portal = ({language}: PortalProps) => {
    const [activeLayer, setActiveLayer] = useState<DataLayer>('heat');
  const [rightBarTab, setRightBarTab] = useState<'Legend' | 'Analysis'>('Legend');
    // const [language, setLanguage] = useState<Language>('en');
    const [showMobilePanel, setShowMobilePanel] = useState(false);
    const [selectedFeature, setSelectedFeature] = useState<SelectedFeature | null>(null);
    const [selectedYear, setSelectedYear] = useState('2024');
    const [mapCenter, setMapCenter] = useState<[number, number] | null>(null);
    const [layerSelections, setLayerSelections] = useState<Record<DataLayer, LayerSelectionValue>>(
      () =>
        layerRegistry.reduce((accumulator, layer) => {
          accumulator[layer.id] = {};
          return accumulator;
        }, {} as Record<DataLayer, LayerSelectionValue>)
    );
    const [layerSelectionOptions, setLayerSelectionOptions] = useState<
      Record<DataLayer, Partial<Record<SelectorKey, LayerSelectOption[]>>>
    >(() => layerRegistry.reduce((accumulator, layer) => {
      accumulator[layer.id] = {};
      return accumulator;
    }, {} as Record<DataLayer, Partial<Record<SelectorKey, LayerSelectOption[]>>>));

    const handleLocationSelect = (location: { name: string; coords: [number, number] }) => {
        setMapCenter(location.coords);
      };

    const handleSelectionChange = (layer: DataLayer, field: SelectorKey, value?: string) => {
      const layerConfig = layerRegistry.find((item) => item.id === layer);
      const selectors = layerConfig?.selection?.selectors || [];

      setLayerSelections((previous) => {
        const currentLayerSelection = previous[layer] || {};
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
          [layer]: nextLayerSelection,
        };
      });

      if (layer === 'modeled' && field === 'year' && value) {
        setSelectedYear(value);
      }
    };

    useEffect(() => {
      const activeConfig = layerRegistry.find((item) => item.id === activeLayer);
      const selectors = activeConfig?.selection?.selectors || [];
      const activeSelection = layerSelections[activeLayer] || {};

      selectors.forEach((selector) => {
        const dependenciesSatisfied = (selector.dependsOn || []).every((dependency) => Boolean(activeSelection[dependency]));
        if (!dependenciesSatisfied) {
          setLayerSelectionOptions((previous) => ({
            ...previous,
            [activeLayer]: {
              ...previous[activeLayer],
              [selector.key]: [],
            },
          }));
          return;
        }

        fetchSelectorOptions({
          layerId: activeLayer,
          field: selector.key,
          selection: activeSelection,
        })
          .then((options) => {
            setLayerSelectionOptions((previous) => ({
              ...previous,
              [activeLayer]: {
                ...previous[activeLayer],
                [selector.key]: options.length ? options : getFallbackSelectorOptions(selector.key, language),
              },
            }));
          })
          .catch(() => {
            setLayerSelectionOptions((previous) => ({
              ...previous,
              [activeLayer]: {
                ...previous[activeLayer],
                [selector.key]: getFallbackSelectorOptions(selector.key, language),
              },
            }));
          });
      });
    }, [activeLayer, layerSelections, language]);

  return (
    <div className="h-full min-h-0 overflow-hidden flex flex-col bg-gray-50">
      
      <div className="flex-1 flex overflow-hidden relative">
        {/* Desktop Sidebar */}
        <div className="hidden lg:flex lg:w-96 flex-col border-r bg-white overflow-hidden">
          <div className="p-4 border-b flex-shrink-0">
            <SearchBar 
              language={language} 
              onLocationSelect={handleLocationSelect}
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            <LayerControls 
              activeLayer={activeLayer} 
              onLayerChange={(layer) => {
                setActiveLayer(layer);
                setRightBarTab('Analysis');
              }}
              language={language}
              selectionValues={layerSelections}
              selectionOptions={layerSelectionOptions}
              onSelectionChange={handleSelectionChange}
            />
          </div>
        </div>

        {/* Map Container */}
        <div className="flex-1 min-h-0 relative">
          <Map 
          />
          <RightBar
            activeLayer={activeLayer}
            language={language}
            selectedFeature={selectedFeature}
            selectedYear={selectedYear}
            onYearChange={setSelectedYear}
            activeTab={rightBarTab}
            onTabChange={setRightBarTab}
          />
          
          {/* Mobile Controls Button */}
          <Button
            className="lg:hidden absolute bottom-4 right-4 z-[1000] shadow-lg"
            size="lg"
            onClick={() => setShowMobilePanel(true)}
          >
            <Menu className="size-5 mr-2" />
            {language === 'en' ? 'Controls' : 'Contrôles'}
          </Button>
        </div>

        {/* Mobile Drawer */}
        <MobileDrawer
          isOpen={showMobilePanel}
          onClose={() => setShowMobilePanel(false)}
          activeLayer={activeLayer}
          onLayerChange={(layer) => {
            setActiveLayer(layer);
            setRightBarTab('Analysis');
          }}
          language={language}
          selectionValues={layerSelections}
          selectionOptions={layerSelectionOptions}
          onSelectionChange={handleSelectionChange}
        />
      </div>
    </div>
  )
}

export default Portal
