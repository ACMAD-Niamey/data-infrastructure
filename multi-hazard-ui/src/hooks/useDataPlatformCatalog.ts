import { useCallback, useEffect, useState } from "react";
import type { CatalogLayer } from "../types/catalogLayer";
import { fetchProjectLayers, getProjectSlug } from "../services/catalogLayersApi";

export function useDataPlatformCatalog() {
  const [layers, setLayers] = useState<CatalogLayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fetched = await fetchProjectLayers(getProjectSlug(), { requireIcon: false });
      setLayers(fetched);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load datasets");
      setLayers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { layers, loading, error, reload };
}
