import { Language } from '../types';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { LayerControls } from './LayerControls';
import { DataPanel } from './DataPanel';
import { ScrollArea } from './ui/scroll-area';
import { DataLayer } from './layers/layerRegistry';

interface MobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeLayer: DataLayer;
  onLayerChange: (layer: DataLayer) => void;
  language: Language;
}

const translations = {
  en: {
    title: 'Dashboard Controls'
  },
  fr: {
    title: 'Contrôles du Tableau de Bord'
  }
};

export function MobileDrawer({ 
  isOpen, 
  onClose, 
  activeLayer, 
  onLayerChange,
  language 
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
            activeLayer={activeLayer}
            onLayerChange={(layer) => {
              onLayerChange(layer);
              onClose();
            }}
            language={language}
          />
          <DataPanel activeLayer={activeLayer} language={language} />
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
