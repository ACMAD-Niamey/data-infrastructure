import { useEffect, useState } from "react";
import type { OpenApiGroup } from "../types/openApiSchema";
import { fetchOpenApiSchema, groupOperations } from "../services/openApiSchema";

export function useOpenApiSchema() {
  const [groups, setGroups] = useState<OpenApiGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchOpenApiSchema()
      .then((schema) => {
        if (cancelled) return;
        setGroups(groupOperations(schema));
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load API schema");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { groups, loading, error };
}
