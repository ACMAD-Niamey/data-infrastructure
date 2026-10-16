import axios from "axios";
import { catalogBaseUrl, tipgBaseUrl } from "../config/api";

export type StationLocation = {
  code: string;
  name: string;
  site: string | null;
  exposure: "sun" | "shade" | null;
  commune: string | null;
  lng: number;
  lat: number;
};

export type SeriesPoint = { period: string; value: number | null };

export type StationSeries = {
  points: SeriesPoint[];
  availableValues: string[];
};

type TipgFeature = {
  geometry: { coordinates: [number, number] };
  properties: Record<string, string | null>;
};

const client = axios.create({ timeout: 20000 });

/** TiPG CQL2 text filter scoping a shared view to one dataset. */
export function datasetFilter(datasetCode: string): string {
  return `dataset_code='${datasetCode.replace(/'/g, "''")}'`;
}

export function stationTileUrl(collection: string, datasetCode: string): string {
  const filter = encodeURIComponent(datasetFilter(datasetCode));
  return `${tipgBaseUrl}/collections/${collection}/tiles/WebMercatorQuad/{z}/{x}/{y}?filter=${filter}`;
}

/** Small list (tens of points): fetched once for bounds and sun/shade pairing. */
export async function fetchStationLocations(
  collection: string,
  datasetCode: string,
): Promise<StationLocation[]> {
  const { data } = await client.get<{ features: TipgFeature[] }>(
    `${tipgBaseUrl}/collections/${collection}/items`,
    { params: { f: "geojson", limit: 1000, filter: datasetFilter(datasetCode) } },
  );
  return data.features.map((f) => ({
    code: f.properties.station_code ?? "",
    name: f.properties.name ?? "",
    site: f.properties.site ?? null,
    exposure: (f.properties.exposure as StationLocation["exposure"]) ?? null,
    commune: f.properties.commune ?? null,
    lng: f.geometry.coordinates[0],
    lat: f.geometry.coordinates[1],
  }));
}

export async function fetchStationRange(code: string): Promise<{ first: string; last: string } | null> {
  const { data } = await client.get(`${catalogBaseUrl}/api/stations/${encodeURIComponent(code)}/`);
  return data.first_observation && data.last_observation
    ? { first: data.first_observation, last: data.last_observation }
    : null;
}

export async function fetchStationSeries(params: {
  code: string;
  variable: string;
  agg: string;
  value: string;
  start: string;
  end: string;
}): Promise<StationSeries> {
  const { code, ...query } = params;
  const { data } = await client.get(
    `${catalogBaseUrl}/api/stations/${encodeURIComponent(code)}/stats/`,
    { params: query },
  );
  return {
    availableValues: data.available_values ?? [],
    // Aggregated buckets carry `avg`; raw rows carry `value`.
    points: (data.data as Array<{ period: string; avg?: number; value?: number }>).map((d) => ({
      period: d.period,
      value: d.avg ?? d.value ?? null,
    })),
  };
}
