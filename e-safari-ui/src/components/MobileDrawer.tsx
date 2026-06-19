import { Language } from '../types';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { LayerControls } from './LayerControls';
import { DataPanel } from './DataPanel';
import { ScrollArea } from './ui/scroll-area';
import type {
  CatalogLayer,
  LayerSelectOption,
  LayerSelectionValue,
  SelectorKey,
} from '../types/catalogLayer';

interface MobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  layers: CatalogLayer[];
  activeLayerId: string | null;
  activeLayer: CatalogLayer | null;
  onLayerChange: (layerId: string) => void;
  onLayerDeactivate: () => void;
  language: Language;
  selectionValues: Record<string, LayerSelectionValue>;
  selectionOptions: Record<string, Partial<Record<SelectorKey, LayerSelectOption[]>>>;
  onSelectionChange: (layerId: string, field: SelectorKey, value?: string) => void;
  loading?: boolean;
  error?: string | null;
  opacity: number;
  onOpacityChange: (value: number) => void;
}

const translations = {
  en: {
    title: 'Dashboard Controls',
  },
  fr: {
    title: 'Contrôles du Tableau de Bord',
  },
};

export function MobileDrawer({
  isOpen,
  onClose,
  layers,
  activeLayerId,
  activeLayer,
  onLayerChange,
  onLayerDeactivate,
  language,
  selectionValues,
  selectionOptions,
  onSelectionChange,
  loading,
  error,
  opacity,
  onOpacityChange,
}: MobileDrawerProps) {
  const t = translations[language];

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="bottom" className="h-[85vh]">
        <SheetHeader>
          <SheetTitle>{t.title}</SheetTitle>
        </SheetHeader>
        <ScrollArea className="h-[calc(85vh-4rem)] mt-4">
          <LayerControls
            layers={layers}
            activeLayerId={activeLayerId}
            onLayerChange={(layerId) => {
              onLayerChange(layerId);
              onClose();
            }}
            onLayerDeactivate={() => {
              onLayerDeactivate();
              onClose();
            }}
            language={language}
            selectionValues={selectionValues}
            selectionOptions={selectionOptions}
            onSelectionChange={onSelectionChange}
            loading={loading}
            error={error}
            opacity={opacity}
            onOpacityChange={onOpacityChange}
          />
          <DataPanel activeLayer={activeLayer} language={language} />
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
