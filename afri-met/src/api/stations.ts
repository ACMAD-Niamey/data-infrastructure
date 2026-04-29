import axios from "axios";
import { getApiBaseUrl } from "../config";
import type {
  StationDetailResponse,
  StationFacetsResponse,
  StationListResponse,
  StationStatsResponse,
} from "./types";

/** Paths are under `/api` on Django; `baseURL` is that `/api` root from config. */
const client = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 60_000,
});

export async function fetchStationList(params: {
  country_code?: string;
  admin1?: string;
  admin2?: string;
}): Promise<StationListResponse> {
  const { data } = await client.get<StationListResponse>("/stations/", {
    params: {
      country_code: params.country_code || undefined,
      admin1: params.admin1 || undefined,
      admin2: params.admin2 || undefined,
    },
  });
  return data;
}

export async function fetchFacets(): Promise<StationFacetsResponse> {
  const { data } = await client.get<StationFacetsResponse>("/stations/facets/");
  return data;
}

export async function fetchStationDetail(stationCode: string): Promise<StationDetailResponse> {
  const { data } = await client.get<StationDetailResponse>(
    `/stations/${encodeURIComponent(stationCode)}/`,
  );
  return data;
}

export async function fetchStationStats(
  stationCode: string,
  query: {
    variable: string;
    agg?: string;
    start?: string;
    end?: string;
  },
): Promise<StationStatsResponse> {
  const { data } = await client.get<StationStatsResponse>(
    `/stations/${encodeURIComponent(stationCode)}/stats/`,
    {
      params: {
        variable: query.variable,
        agg: query.agg ?? "daily",
        start: query.start,
        end: query.end,
      },
    },
  );
  return data;
}
