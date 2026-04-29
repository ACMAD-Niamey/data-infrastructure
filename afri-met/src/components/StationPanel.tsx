import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { X } from "lucide-react";
import { fetchStationDetail, fetchStationStats } from "../api/stations";
import type { StationDetailResponse, StationStatsResponse } from "../api/types";
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

export function StationPanel({ stationCode, onClose }: StationPanelProps) {
  const [detail, setDetail] = useState<StationDetailResponse | null>(null);
  const [stats, setStats] = useState<StationStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const variables = detail?.variables ?? [];

  const [variable, setVariable] = useState("temp");
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
      setDetail(null);
      setStats(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchStationDetail(stationCode)
      .then((d) => {
        if (!cancelled) {
          setDetail(d);
          const first = d.variables[0]?.variable_code;
          if (first) setVariable(first);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message ?? "Failed to load station");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [stationCode]);

  useEffect(() => {
    const first = detail?.variables?.[0]?.variable_code;
    if (first) setVariable(first);
  }, [detail]);

  useEffect(() => {
    if (!stationCode || !detail?.variables?.length) return;

    let cancelled = false;
    setLoading(true);
    fetchStationStats(stationCode, { variable, agg, start, end })
      .then((s) => {
        if (!cancelled) setStats(s);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message ?? "Failed to load series");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [stationCode, detail, variable, agg, start, end]);

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

  if (!stationCode) return null;

  return (
    <div className="flex flex-col gap-3 bg-white text-slate-900 shadow-xl md:shadow-none">
      <div className="flex items-start justify-between gap-2 border-b border-slate-200 pb-2">
        <div>
          <h2 className="text-lg font-semibold leading-tight">
            {detail?.name ?? stationCode}
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

      {loading && <p className="text-sm text-slate-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-2 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
          Variable
          <select
            className="rounded-md border border-slate-300 px-2 py-2 text-sm min-h-[44px]"
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
          >
            {variables.length === 0 ? (
              <option value={variable}>{variable}</option>
            ) : (
              variables.map((v) => (
                <option key={v.variable_code} value={v.variable_code}>
                  {v.variable_code}
                  {v.unit ? ` (${v.unit})` : ""}
                </option>
              ))
            )}
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

      <div className="h-56 w-full min-w-0 pb-[env(safe-area-inset-bottom,0px)]">
        <ResponsiveContainer width="100%" height="100%">
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
        </ResponsiveContainer>
      </div>
    </div>
  );
}
