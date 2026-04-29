export type SpatialExtent = {
  west: number;
  south: number;
  east: number;
  north: number;
};

export type StationListItem = {
  id: number;
  station_code: string;
  name: string | null;
  country_code: string | null;
  admin1?: string | null;
  admin2?: string | null;
  station_type: string | null;
  elevation_m: number | null;
  latitude: number | null;
  longitude: number | null;
  variables_available: string[];
  latest_observed_at: string | null;
};

export type StationListResponse = {
  count: number;
  results: StationListItem[];
  extent: SpatialExtent | null;
};

export type StationFacetsResponse = {
  countries: string[];
  admin1: string[];
  admin2: string[];
};

export type VariableSummary = {
  variable_code: string;
  unit: string | null;
  record_count: number;
  first_observation: string | null;
  last_observation: string | null;
};

export type StationDetailResponse = {
  id: number;
  station_code: string;
  name: string | null;
  country_code: string | null;
  station_type: string | null;
  is_active: boolean;
  elevation_m: number | null;
  latitude: number | null;
  longitude: number | null;
  total_records: number;
  first_observation: string | null;
  last_observation: string | null;
  variables: VariableSummary[];
};

export type StatsAggRow = {
  period: string;
  avg?: number | null;
  min?: number | null;
  max?: number | null;
  count?: number | null;
};

export type StatsRawRow = {
  period: string;
  value: number | null;
  unit: string | null;
};

export type StationStatsResponse = {
  station_code: string;
  station_name: string | null;
  variable: string;
  aggregation: string;
  start: string;
  end: string;
  data: StatsAggRow[] | StatsRawRow[];
};
