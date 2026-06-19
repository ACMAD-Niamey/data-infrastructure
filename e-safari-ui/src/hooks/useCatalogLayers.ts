import { useCallback, useEffect, useMemo, useState } from "react";
import type { Language } from "../types";
import type { CatalogLayer, LayerSelectionValue } from "../types/catalogLayer";
import { deriveSelectors } from "../lib/cadenceSelectors";
import { fetchProjectLayers, getProjectSlug } from "../services/catalogLayersApi";

export function useCatalogLayers(language: Language) {
  const [layers, setLayers] = useState<CatalogLayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeLayerIds, setActiveLayerIds] = useState<string[]>([]);

  const toggleActiveLayer = useCallback((id: string) => {
    setActiveLayerIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

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
      setActiveLayerIds((current) => {
        // Keep existing active layers that are still present; otherwise default to the first layer.
        const stillValid = current.filter((id) => withLang.some((l) => l.id === id));
        if (stillValid.length > 0) return stillValid;
        const first = withLang[0]?.id;
        return first ? [first] : [];
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load layers");
      setLayers([]);
      setActiveLayerIds([]);
    } finally {
      setLoading(false);
    }
  }, [language]);

  useEffect(() => {
    reload();
  }, [reload]);

  const activeLayers = useMemo(
    () => layers.filter((layer) => activeLayerIds.includes(layer.id)),
    [layers, activeLayerIds],
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
    activeLayerIds,
    activeLayers,
    toggleActiveLayer,
    layerSelections,
    setLayerSelections,
    reload,
  };
}
