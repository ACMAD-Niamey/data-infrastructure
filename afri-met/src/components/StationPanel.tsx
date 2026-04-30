import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { X } from "lucide-react";
import { fetchStationDetail, fetchStationStats } from "../api/stations";
import type { StationDetailResponse, StationStatsResponse } from "../api/types";
import { ChartRefreshingOverlay, ChartSkeleton } from "./ChartSkeleton";
import { buildWindRoseRows, resolveWindVariables } from "./windRose";
function formatAxisLabel(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "2-digit" });
  } catch {
    return iso;
  }
}

function formatTooltipDate(iso: string, aggregation: string) {
  try {
    const d = new Date(iso);
    const includeTime = aggregation === "raw" || aggregation === "hourly";
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
    });
  } catch {
    return iso;
  }
}

function formatNumericValue(value: number | string | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "N/A";
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function SeriesTooltip({
  active,
  payload,
  label,
  aggregation,
  seriesName,
}: {
  active?: boolean;
  payload?: Array<{ value?: number; name?: string }>;
  label?: string;
  aggregation: string;
  seriesName: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0];
  return (
    <div className="rounded-md border border-slate-200 bg-white/95 px-3 py-2 text-xs shadow-md backdrop-blur">
      <p className="font-semibold text-slate-700">{formatTooltipDate(label ?? "", aggregation)}</p>
      <p className="mt-1 text-slate-600">
        {seriesName}: <span className="font-semibold text-slate-800">{formatNumericValue(point.value)}</span>
      </p>
    </div>
  );
}

type StationPanelProps = {
  stationCode: string | null;
  onClose: () => void;
};

type ViewMode = "single" | "wind";
type ChartType = "line" | "bar" | "area" | "wind_rose";

const DEFAULT_VARIABLE_OPTIONS = [
  "temp",
  "dewpoint",
  "rh",
  "pressure",
  "wind_speed",
  "wind_direction",
  "rainfall",
  "visibility",
];

export function StationPanel({ stationCode, onClose }: StationPanelProps) {
  const [stats, setStats] = useState<StationStatsResponse | null>(null);
  const [windSpeedStats, setWindSpeedStats] = useState<StationStatsResponse | null>(null);
  const [windDirectionStats, setWindDirectionStats] = useState<StationStatsResponse | null>(null);
  const [stationDetail, setStationDetail] = useState<StationDetailResponse | null>(null);
  const [isSeriesLoading, setIsSeriesLoading] = useState(false);
  const [hasLoadedSeries, setHasLoadedSeries] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Derive available variable codes from station detail; fall back to DEFAULT_VARIABLE_OPTIONS
  // while the detail is loading so the dropdown is not empty.
  const availableVariables = useMemo(
    () =>
      stationDetail
        ? stationDetail.variables.map((v) => v.variable_code)
        : DEFAULT_VARIABLE_OPTIONS,
    [stationDetail],
  );

  const windVars = useMemo(() => resolveWindVariables(availableVariables), [availableVariables]);

  const [variable, setVariable] = useState("temp");
  const [viewMode, setViewMode] = useState<ViewMode>("single");
  const [chartType, setChartType] = useState<ChartType>("line");
  const [agg, setAgg] = useState("daily");

  const defaultRange = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 30);
    return {
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
    };
  }, []);

  const [start, setStart] = useState(defaultRange.start);
  const [end, setEnd] = useState(defaultRange.end);

  useEffect(() => {
    if (!stationCode) {
      setStationDetail(null);
      return;
    }
    let cancelled = false;
    fetchStationDetail(stationCode)
      .then((detail) => {
        if (!cancelled) setStationDetail(detail);
      })
      .catch(() => {
        // Non-fatal: windVars will fall back to DEFAULT_VARIABLE_OPTIONS.
      });
    return () => {
      cancelled = true;
    };
  }, [stationCode]);

  // When available variables change (new station selected), reset variable selection
  // to the first available code if the current selection is no longer valid.
  useEffect(() => {
    if (availableVariables.length > 0 && !availableVariables.includes(variable)) {
      setVariable(availableVariables[0]);
    }
  }, [availableVariables, variable]);

  useEffect(() => {
    if (!windVars.hasWindPair && viewMode === "wind") {
      setViewMode("single");
      setChartType("line");
      return;
    }
    if (windVars.hasWindPair && viewMode === "single") {
      setViewMode("single");
    }
  }, [windVars.hasWindPair, viewMode]);

  useEffect(() => {
    if (viewMode === "wind") {
      setChartType("wind_rose");
      return;
    }
    if (agg === "monthly" || agg === "yearly") {
      setChartType((prev) => (prev === "wind_rose" ? "bar" : prev));
      return;
    }
    setChartType((prev) => (prev === "wind_rose" ? "line" : prev));
  }, [viewMode, agg]);

  useEffect(() => {
    if (!stationCode) {
      setStats(null);
      setWindSpeedStats(null);
      setWindDirectionStats(null);
      setHasLoadedSeries(false);
      return;
    }

    let cancelled = false;
    setIsSeriesLoading(true);
    setError(null);

    if (viewMode === "wind" && windVars.hasWindPair && windVars.speedVariable && windVars.directionVariable) {
      Promise.all([
        fetchStationStats(stationCode, {
          variable: windVars.speedVariable,
          agg,
          start,
          end,
        }),
        fetchStationStats(stationCode, {
          variable: windVars.directionVariable,
          agg,
          start,
          end,
        }),
      ])
        .then(([speed, direction]) => {
          if (!cancelled) {
            setWindSpeedStats(speed);
            setWindDirectionStats(direction);
            setStats(null);
            setHasLoadedSeries(true);
          }
        })
        .catch((e: Error) => {
          if (!cancelled) setError(e.message ?? "Failed to load wind series");
        })
        .finally(() => {
          if (!cancelled) setIsSeriesLoading(false);
        });
    } else {
      fetchStationStats(stationCode, { variable, agg, start, end })
        .then((s) => {
          if (!cancelled) {
            setStats(s);
            setWindSpeedStats(null);
            setWindDirectionStats(null);
            setHasLoadedSeries(true);
          }
        })
        .catch((e: Error) => {
          if (!cancelled) setError(e.message ?? "Failed to load series");
        })
        .finally(() => {
          if (!cancelled) setIsSeriesLoading(false);
        });
    }

    return () => {
      cancelled = true;
    };
  }, [stationCode, variable, agg, start, end, viewMode, windVars]);

  const chartRows = useMemo(() => {
    if (!stats?.data?.length) return [];
    if (stats.aggregation === "raw") {
      return (stats.data as { period: string; value: number | null }[]).map((row) => ({
        t: row.period,
        label: formatAxisLabel(row.period),
        value: row.value,
      }));
    }
    return (
      stats.data as {
        period: string;
        avg?: number | null;
      }[]
    ).map((row) => ({
      t: row.period,
      label: formatAxisLabel(row.period),
      value: row.avg,
    }));
  }, [stats]);
  const windRoseRows = useMemo(() => {
    if (!windSpeedStats || !windDirectionStats) return [];
    return buildWindRoseRows(windSpeedStats, windDirectionStats);
  }, [windSpeedStats, windDirectionStats]);
  const isChartLoading = isSeriesLoading && !hasLoadedSeries;
  const isChartRefreshing = isSeriesLoading && hasLoadedSeries;

  if (!stationCode) return null;

  return (
    <div className="flex flex-col gap-4 bg-white text-slate-900 shadow-xl md:shadow-none">
      <div className="flex items-start justify-between gap-2 border-b border-slate-200 pb-2">
        <div>
          <h2 className="text-lg font-semibold leading-tight text-slate-900">
            {stationCode}
          </h2>
          <p className="text-xs text-slate-500">Interactive series explorer</p>
        </div>
        <button
          type="button"
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Close"
          onClick={onClose}
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50/60 p-2 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          View
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as ViewMode)}
          >
            <option value="single">Variable</option>
            {windVars.hasWindPair ? <option value="wind">Wind</option> : null}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          Chart
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={chartType}
            onChange={(e) => setChartType(e.target.value as ChartType)}
            disabled={viewMode === "wind"}
          >
            <option value="line">line</option>
            <option value="bar">bar</option>
            <option value="area">area</option>
            {viewMode === "wind" ? <option value="wind_rose">wind rose</option> : null}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          Variable
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
            disabled={viewMode === "wind"}
          >
            {availableVariables.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          Aggregation
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={agg}
            onChange={(e) => setAgg(e.target.value)}
          >
            <option value="daily">daily</option>
            <option value="hourly">hourly</option>
            <option value="monthly">monthly</option>
            <option value="yearly">yearly</option>
            <option value="raw">raw</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          Start
          <input
            type="date"
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
          End
          <input
            type="date"
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
      </div>
      {viewMode === "wind" && !windVars.hasWindPair ? (
        <p className="text-xs text-amber-700">
          Wind view requires both wind speed and wind direction variables for this station.
        </p>
      ) : null}

      <div className="relative h-60 w-full min-w-0 overflow-hidden rounded-lg border border-slate-200 bg-white pb-[env(safe-area-inset-bottom,0px)]">
        {isChartLoading ? (
          <ChartSkeleton />
        ) : viewMode === "wind" ? (
          windRoseRows.some((row) => row.count > 0) ? (
            <>
              <ChartRefreshingOverlay active={isChartRefreshing} />
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={windRoseRows} outerRadius="75%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="sector" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value: number) => value.toFixed(2)} contentStyle={{ borderRadius: 8, borderColor: "#cbd5e1" }} />
                  <Radar dataKey="value" name="wind speed" fill="#0ea5e9" fillOpacity={0.35} stroke="#0284c7" />
                </RadarChart>
              </ResponsiveContainer>
            </>
          ) : (
            <div className="flex h-full items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-3 text-center text-sm text-slate-600">
              No compatible wind speed and direction data in this date range.
            </div>
          )
        ) : (
          <>
            <ChartRefreshingOverlay active={isChartRefreshing} />
            <ResponsiveContainer width="100%" height="100%">
              {chartType === "bar" ? (
                <BarChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.7} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    cursor={{ fill: "#bae6fd", fillOpacity: 0.18 }}
                    content={<SeriesTooltip aggregation={agg} seriesName={variable} />}
                  />
                  <Bar dataKey="value" name={variable} fill="#0ea5e9" />
                </BarChart>
              ) : chartType === "area" ? (
                <AreaChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.7} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    cursor={{ stroke: "#7dd3fc", strokeOpacity: 0.45, strokeWidth: 1.5 }}
                    content={<SeriesTooltip aggregation={agg} seriesName={variable} />}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    name={variable}
                    stroke="#0284c7"
                    fill="#0ea5e9"
                    fillOpacity={0.22}
                    connectNulls
                    activeDot={{ r: 4, fill: "#0369a1", stroke: "#ffffff", strokeWidth: 1.5 }}
                  />
                </AreaChart>
              ) : (
                <LineChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.7} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    cursor={{ stroke: "#7dd3fc", strokeOpacity: 0.45, strokeWidth: 1.5 }}
                    content={<SeriesTooltip aggregation={agg} seriesName={variable} />}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name={variable}
                    stroke="#0284c7"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: "#0369a1", stroke: "#ffffff", strokeWidth: 1.5 }}
                    connectNulls
                  />
                </LineChart>
              )}
            </ResponsiveContainer>
          </>
        )}
      </div>
    </div>
  );
}
