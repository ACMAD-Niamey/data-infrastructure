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
import { fetchStationStats } from "../api/stations";
import type { StationStatsResponse } from "../api/types";
import { ChartRefreshingOverlay, ChartSkeleton } from "./ChartSkeleton";
import { buildWindRoseRows, resolveWindVariables } from "./windRose";
function formatDayLabel(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return iso;
  }
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
  const [isSeriesLoading, setIsSeriesLoading] = useState(false);
  const [hasLoadedSeries, setHasLoadedSeries] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const windVars = useMemo(() => resolveWindVariables(DEFAULT_VARIABLE_OPTIONS), []);

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
        label: formatDayLabel(row.period),
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
      label: formatDayLabel(row.period),
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
    <div className="flex flex-col gap-3 bg-white text-slate-900 shadow-xl md:shadow-none">
      <div className="flex items-start justify-between gap-2 border-b border-slate-200 pb-2">
        <div>
          <h2 className="text-lg font-semibold leading-tight">
            {stationCode}
          </h2>
          <p className="text-xs text-slate-500">{stationCode}</p>
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

      <div className="grid gap-2 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
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

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
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

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          Variable
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
            disabled={viewMode === "wind"}
          >
            {DEFAULT_VARIABLE_OPTIONS.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
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

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          Start
          <input
            type="date"
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
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

      <div className="relative h-56 w-full min-w-0 pb-[env(safe-area-inset-bottom,0px)]">
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
                  <Tooltip formatter={(value: number) => value.toFixed(2)} />
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
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" name={variable} fill="#0ea5e9" />
                </BarChart>
              ) : chartType === "area" ? (
                <AreaChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="value"
                    name={variable}
                    stroke="#0284c7"
                    fill="#0ea5e9"
                    fillOpacity={0.25}
                    connectNulls
                  />
                </AreaChart>
              ) : (
                <LineChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={8} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name={variable}
                    stroke="#0284c7"
                    strokeWidth={2}
                    dot={false}
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
