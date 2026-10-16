import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Language } from "../../types";
import type { LayerSelectionValue } from "../../types/catalogLayer";
import { ALL_VARIABLES, ALL_VIEW_VARIABLES, STATION_VARIABLES, variableMeta } from "../../lib/stationSelectors";
import { fetchStationRange, fetchStationSeries } from "../../services/stationsApi";
import type { StationLocation } from "../../services/stationsApi";

type Props = {
  /** Every sensor at the open location (usually a sun + a shade pair). */
  sensors: StationLocation[];
  selection: LayerSelectionValue;
  language: Language;
};

// Same colours as the map points; the key itself lives on the Legend tab.
export const EXPOSURE_COLORS = { sun: "#f59e0b", shade: "#2563eb", other: "#6b7280" } as const;
const RAW_WINDOW_DAYS = 3; // the API caps raw rows at 5000 (~3.5 days at 1/min)

const copy = {
  en: { loading: "Loading…", empty: "No data for this selection.", error: "Could not load the series.",
        sun: "Sun", shade: "Shade", hidden: "These values are not published for this dataset." },
  fr: { loading: "Chargement…", empty: "Aucune donnée pour cette sélection.", error: "Impossible de charger la série.",
        sun: "Soleil", shade: "Ombre", hidden: "Ces valeurs ne sont pas publiées pour ce jeu de données." },
};

type Row = { period: string } & Record<string, number | string | null>;
type Span = { start: string; end: string };

function seriesFor(sensors: StationLocation[], t: (typeof copy)["en"]) {
  return sensors.map((s) => ({
    field: s.exposure ?? s.code,
    color: EXPOSURE_COLORS[s.exposure ?? "other"],
    label: s.exposure ? t[s.exposure] : s.code,
  }));
}

/** Orange sun / blue shade key, pinned under the location name while charts scroll. */
function SensorLegend({ sensors, t }: { sensors: StationLocation[]; t: (typeof copy)["en"] }) {
  return (
    <div className="flex items-center gap-4 mt-1" aria-label="legend">
      {seriesFor(sensors, t).map((s) => (
        <span key={s.field} className="inline-flex items-center gap-1.5 text-gray-700">
          <span style={{ width: 12, height: 12, borderRadius: 6, background: s.color, display: "inline-block" }} />
          {s.label}
        </span>
      ))}
    </div>
  );
}

type ChartProps = {
  sensors: StationLocation[];
  variable: string;
  agg: string;
  value: string;
  span: Span;
  language: Language;
  height: number;
  showLegend: boolean;
};

function VariableChart({ sensors, variable, agg, value, span, language, height, showLegend }: ChartProps) {
  const t = copy[language];
  const meta = variableMeta(variable);
  const [rows, setRows] = useState<Row[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "hidden">("loading");
  const key = sensors.map((s) => s.code).join(",");

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    Promise.all(
      sensors.map((s) => fetchStationSeries({ code: s.code, variable, agg, value, ...span })),
    )
      .then((results) => {
        if (cancelled) return;
        const byPeriod = new Map<string, Row>();
        results.forEach((res, i) => {
          const field = sensors[i].exposure ?? sensors[i].code;
          res.points.forEach((p) => {
            const row = byPeriod.get(p.period) ?? { period: p.period };
            row[field] = p.value;
            byPeriod.set(p.period, row);
          });
        });
        setRows([...byPeriod.values()].sort((a, b) => a.period.localeCompare(b.period)));
        setStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        // 403 = this value flavour is hidden by the dataset page.
        setStatus(err?.response?.status === 403 ? "hidden" : "error");
      });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, variable, agg, value, span.start, span.end]);

  const series = useMemo(() => seriesFor(sensors, t), [sensors, t]);

  const formatTick = (iso: string) =>
    new Date(iso).toLocaleDateString(language, agg === "raw"
      ? { day: "2-digit", month: "short", hour: "2-digit" }
      : { day: "2-digit", month: "short" });

  if (status === "loading") return <p className="text-gray-500">{t.loading}</p>;
  if (status === "error") return <p className="text-red-600">{t.error}</p>;
  if (status === "hidden") return <p className="text-gray-500">{t.hidden}</p>;
  if (rows.length === 0) return <p className="text-gray-500">{t.empty}</p>;

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="period" tickFormatter={formatTick} minTickGap={32} fontSize={10} />
          <YAxis fontSize={10} domain={["auto", "auto"]} />
          <Tooltip
            labelFormatter={(l) => new Date(String(l)).toLocaleString(language)}
            formatter={(v: number) => [`${Number(v).toFixed(1)} ${meta?.unit ?? ""}`]}
          />
          {showLegend && <Legend />}
          {series.map((s) => (
            <Line key={s.field} dataKey={s.field} name={s.label} stroke={s.color}
                  dot={false} strokeWidth={1.5} connectNulls isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StationAnalysis({ sensors: unordered, selection, language }: Props) {
  const t = copy[language];
  // Sun first: the API/TiPG return sensors in arbitrary order, and the legend reads better stable.
  const sensors = useMemo(
    () => [...unordered].sort((a, b) => (a.exposure === "sun" ? -1 : 0) - (b.exposure === "sun" ? -1 : 0)),
    [unordered],
  );
  const variable = selection.variable ?? ALL_VARIABLES;
  const agg = selection.agg ?? "hourly";
  const value = selection.value ?? "raw";
  const isAll = variable === ALL_VARIABLES;

  const [span, setSpan] = useState<Span | null>(null);
  const key = sensors.map((s) => s.code).join(",");

  // One range lookup shared by every chart: the span the sensors actually recorded.
  useEffect(() => {
    let cancelled = false;
    setSpan(null);
    Promise.all(sensors.map((s) => fetchStationRange(s.code)))
      .then((all) => {
        if (cancelled) return;
        const ranges = all.filter(Boolean) as { first: string; last: string }[];
        if (!ranges.length) return setSpan({ start: "", end: "" });
        const end = new Date(Math.max(...ranges.map((r) => +new Date(r.last))));
        let start = new Date(Math.min(...ranges.map((r) => +new Date(r.first))));
        if (agg === "raw") start = new Date(Math.max(+start, +end - RAW_WINDOW_DAYS * 86400000));
        const day = (d: Date) => d.toISOString().slice(0, 10);
        setSpan({ start: day(start), end: day(end) });
      })
      .catch(() => !cancelled && setSpan({ start: "", end: "" }));
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, agg]);

  const common = { sensors, agg, value, language };
  const variables = isAll ? ALL_VIEW_VARIABLES : STATION_VARIABLES.filter((v) => v.value === variable);

  return (
    <div style={{ fontSize: 12 }}>
      {/* Sticky within the panel's own scroll area (#contentContainer), so the location
          and the colour key stay visible while the stacked charts scroll underneath. */}
      <div
        className="px-3 pt-3 pb-2"
        style={{ position: "sticky", top: 0, zIndex: 2, background: "#fff", borderBottom: "1px solid #e5e7eb" }}
      >
        <div className="font-semibold text-gray-800">{sensors[0]?.site ?? sensors[0]?.name}</div>
        <div className="text-gray-500">
          {sensors[0]?.commune ? `${sensors[0].commune}` : ""}
          {!isAll && variableMeta(variable) ? ` · ${variableMeta(variable)![language]} (${variableMeta(variable)!.unit})` : ""}
        </div>
        <SensorLegend sensors={sensors} t={t} />
      </div>

      <div className="p-3">
      {!span && <p className="text-gray-500">{t.loading}</p>}
      {span && !span.start && <p className="text-gray-500">{t.empty}</p>}

      {span?.start && variables.map((v) => (
        <div key={v.value} className={isAll ? "mb-4" : ""}>
          {isAll && (
            <div className="font-medium text-gray-700 mb-1">{v[language]} ({v.unit})</div>
          )}
          <VariableChart {...common} variable={v.value} span={span}
                         height={isAll ? 150 : 240} showLegend={!isAll} />
        </div>
      ))}
      </div>
    </div>
  );
}
