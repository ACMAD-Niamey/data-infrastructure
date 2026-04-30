import type { StationStatsResponse, StatsAggRow, StatsRawRow } from "../api/types";

export type WindRoseRow = {
  sector: string;
  value: number;
  count: number;
};

const SECTOR_COUNT = 16;
const DEGREES_PER_SECTOR = 360 / SECTOR_COUNT;
const SECTOR_LABELS = [
  "N",
  "NNE",
  "NE",
  "ENE",
  "E",
  "ESE",
  "SE",
  "SSE",
  "S",
  "SSW",
  "SW",
  "WSW",
  "W",
  "WNW",
  "NW",
  "NNW",
];

function toSeriesMap(stats: StationStatsResponse): Map<string, number | null> {
  const rows = stats.data as (StatsAggRow | StatsRawRow)[];
  const map = new Map<string, number | null>();

  rows.forEach((row) => {
    const value = "value" in row ? row.value : row.avg ?? null;
    map.set(row.period, typeof value === "number" ? value : null);
  });
  return map;
}

function toSectorIndex(deg: number): number {
  const normalized = ((deg % 360) + 360) % 360;
  const shifted = normalized + DEGREES_PER_SECTOR / 2;
  return Math.floor(shifted / DEGREES_PER_SECTOR) % SECTOR_COUNT;
}

export function buildWindRoseRows(
  speedStats: StationStatsResponse,
  directionStats: StationStatsResponse,
): WindRoseRow[] {
  const speedByPeriod = toSeriesMap(speedStats);
  const directionByPeriod = toSeriesMap(directionStats);
  const bucketTotals = Array.from({ length: SECTOR_COUNT }, () => ({
    speedTotal: 0,
    count: 0,
  }));

  directionByPeriod.forEach((direction, period) => {
    const speed = speedByPeriod.get(period);
    if (typeof direction !== "number" || typeof speed !== "number") return;
    const idx = toSectorIndex(direction);
    bucketTotals[idx].speedTotal += speed;
    bucketTotals[idx].count += 1;
  });

  return bucketTotals.map((bucket, index) => ({
    sector: SECTOR_LABELS[index],
    value: bucket.count > 0 ? bucket.speedTotal / bucket.count : 0,
    count: bucket.count,
  }));
}

const WIND_SPEED_CANDIDATES = ["wind_speed", "windspeed", "ws", "ff", "wind_spd", "wspd"];
const WIND_DIRECTION_CANDIDATES = ["wind_direction", "winddirection", "wd", "dd", "wind_dir", "wdir"];

function normalize(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function findVariable(codes: string[], candidates: string[]): string | null {
  const normalizedCodes = codes.map((code) => ({ code, key: normalize(code) }));
  for (const candidate of candidates) {
    const hit = normalizedCodes.find(({ key }) => key === normalize(candidate) || key.includes(normalize(candidate)));
    if (hit) return hit.code;
  }
  return null;
}

export function resolveWindVariables(codes: string[]): {
  speedVariable: string | null;
  directionVariable: string | null;
  hasWindPair: boolean;
} {
  const speedVariable = findVariable(codes, WIND_SPEED_CANDIDATES);
  const directionVariable = findVariable(codes, WIND_DIRECTION_CANDIDATES);
  return {
    speedVariable,
    directionVariable,
    hasWindPair: Boolean(speedVariable && directionVariable),
  };
}
