import axios from "axios";
import { catalogBaseUrl } from "../config/api";
import type {
  OpenApiGroup,
  OpenApiOperation,
  OpenApiParameter,
  OpenApiSubgroup,
  RawOpenApiOperation,
  RawOpenApiParameter,
  RawOpenApiSchema,
} from "../types/openApiSchema";

const PUBLIC_PATH_PREFIXES = ["/api/catalog/"];
const HTTP_METHODS = ["get"] as const;

// Project-level endpoints (config, countries) are hidden from the reference for now —
// only the dataset/catalog-browsing endpoints are shown.
const EXCLUDED_PATHS = new Set([
  "/api/catalog/projects/{slug}/config/",
  "/api/catalog/projects/{slug}/countries/",
]);

const client = axios.create({ baseURL: catalogBaseUrl, timeout: 15000 });

export async function fetchOpenApiSchema(): Promise<RawOpenApiSchema> {
  const response = await client.get<RawOpenApiSchema>("/api/schema/", {
    params: { format: "json" },
  });
  return response.data;
}

function toParameter(raw: RawOpenApiParameter): OpenApiParameter {
  return {
    name: raw.name,
    in: raw.in,
    required: Boolean(raw.required),
    description: raw.description,
    schema: raw.schema,
  };
}

function mergeParameters(
  pathLevel: RawOpenApiParameter[],
  operationLevel: RawOpenApiParameter[],
): OpenApiParameter[] {
  const byKey = new Map<string, RawOpenApiParameter>();
  for (const p of pathLevel) byKey.set(`${p.in}:${p.name}`, p);
  for (const p of operationLevel) byKey.set(`${p.in}:${p.name}`, p);
  return Array.from(byKey.values()).map(toParameter);
}

function humanize(segment: string): string {
  const withSpaces = segment.replace(/[-_]/g, " ");
  return withSpaces.charAt(0).toUpperCase() + withSpaces.slice(1);
}

function isPathParam(segment: string): boolean {
  return segment.startsWith("{") && segment.endsWith("}");
}

/** Groups public, GET-only catalog operations for the sidebar: primary group = first
 * segment after `/api/`, secondary group = first literal (non-`{param}`) segment
 * after that, falling back to "General" when the path has none. Stations,
 * observations, and project config/countries are excluded for now. */
export function groupOperations(schema: RawOpenApiSchema): OpenApiGroup[] {
  const groups = new Map<string, { label: string; subgroups: Map<string, OpenApiSubgroup> }>();

  for (const [path, pathItem] of Object.entries(schema.paths || {})) {
    if (!PUBLIC_PATH_PREFIXES.some((prefix) => path.startsWith(prefix))) continue;
    if (EXCLUDED_PATHS.has(path)) continue;

    const segments = path.split("/").filter(Boolean);
    const primaryKey = segments[1];
    if (!primaryKey) continue;

    const secondarySegment = segments.slice(2).find((s) => !isPathParam(s));
    const secondaryKey = secondarySegment ?? "general";
    const secondaryLabel = secondarySegment ? humanize(secondarySegment) : "General";

    for (const method of HTTP_METHODS) {
      const op: RawOpenApiOperation | undefined = pathItem[method];
      if (!op) continue;

      const operation: OpenApiOperation = {
        operationId: op.operationId ?? `${method}_${path}`,
        method: method.toUpperCase(),
        path,
        summary: op.summary,
        description: op.description,
        tags: op.tags ?? [primaryKey],
        parameters: mergeParameters(pathItem.parameters ?? [], op.parameters ?? []),
      };

      if (!groups.has(primaryKey)) {
        groups.set(primaryKey, { label: humanize(primaryKey), subgroups: new Map() });
      }
      const group = groups.get(primaryKey)!;
      if (!group.subgroups.has(secondaryKey)) {
        group.subgroups.set(secondaryKey, { key: secondaryKey, label: secondaryLabel, operations: [] });
      }
      group.subgroups.get(secondaryKey)!.operations.push(operation);
    }
  }

  return Array.from(groups.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, { label, subgroups }]) => ({
      key,
      label,
      subgroups: Array.from(subgroups.values())
        .sort((a, b) => a.label.localeCompare(b.label))
        .map((sg) => ({ ...sg, operations: [...sg.operations].sort((a, b) => a.path.localeCompare(b.path)) })),
    }));
}
