import { useCallback, useEffect, useMemo, useState } from "react";
import type { Language } from "../types";
import type { CatalogLayer, LayerSelectionValue } from "../types/catalogLayer";
import { deriveSelectors } from "../lib/cadenceSelectors";
import { fetchProjectLayers, getProjectSlug } from "../services/catalogLayersApi";

export function useCatalogLayers(language: Language) {
  const [layers, setLayers] = useState<CatalogLayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeLayerId, setActiveLayerId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const projectSlug = getProjectSlug();
      const fetched = await fetchProjectLayers(projectSlug);
      const withLang = fetched.map((layer) => ({
        ...layer,
        selectors: deriveSelectors(layer.dataset.cadence, language),
        labels: {
          title: { en: layer.title, fr: layer.title },
          description: {
            en: layer.description.plain,
            fr: layer.description.plain,
          },
        },
      }));
      setLayers(withLang);
      setActiveLayerId((current) => {
        if (current && withLang.some((l) => l.id === current)) {
          return current;
        }
        return withLang[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load layers");
      setLayers([]);
      setActiveLayerId(null);
    } finally {
      setLoading(false);
    }
  }, [language]);

  useEffect(() => {
    reload();
  }, [reload]);

  const activeLayer = useMemo(
    () => layers.find((layer) => layer.id === activeLayerId) ?? null,
    [layers, activeLayerId],
  );

  const [layerSelections, setLayerSelections] = useState<
    Record<string, LayerSelectionValue>
  >({});

  useEffect(() => {
    setLayerSelections((previous) => {
      const next = { ...previous };
      layers.forEach((layer) => {
        if (!next[layer.id]) {
          next[layer.id] = {};
        }
      });
      return next;
    });
  }, [layers]);

  return {
    layers,
    loading,
    error,
    activeLayerId,
    activeLayer,
    setActiveLayerId,
    layerSelections,
    setLayerSelections,
    reload,
  };
}
