import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Language } from "../../types";
import type { LayerSelectionValue } from "../../types/catalogLayer";
import { variableMeta } from "../../lib/stationSelectors";
import {
  fetchStationRange, fetchStationSeries,
} from "../../services/stationsApi";
import type { StationLocation } from "../../services/stationsApi";

type Props = {
  /** Every sensor at the open location (usually a sun + a shade pair). */
  sensors: StationLocation[];
  selection: LayerSelectionValue;
  language: Language;
};

const COLORS = { sun: "#f59e0b", shade: "#2563eb", other: "#6b7280" } as const;
const RAW_WINDOW_DAYS = 3; // the API caps raw rows at 5000 (~3.5 days at 1/min)

const copy = {
  en: { loading: "Loading…", empty: "No data for this selection.", error: "Could not load the series.",
        sun: "Sun", shade: "Shade", hidden: "These values are not published for this dataset." },
  fr: { loading: "Chargement…", empty: "Aucune donnée pour cette sélection.", error: "Impossible de charger la série.",
        sun: "Soleil", shade: "Ombre", hidden: "Ces valeurs ne sont pas publiées pour ce jeu de données." },
};

type Row = { period: string } & Record<string, number | string | null>;

export function StationAnalysis({ sensors, selection, language }: Props) {
  const t = copy[language];
  const variable = selection.variable ?? "temp";
  const agg = selection.agg ?? "hourly";
  const value = selection.value ?? "raw";
  const meta = variableMeta(variable);

  const [rows, setRows] = useState<Row[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "hidden">("loading");
  const key = sensors.map((s) => s.code).join(",");

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    (async () => {
      // Use the span the sensors actually recorded, not a fixed window.
      const ranges = (await Promise.all(sensors.map((s) => fetchStationRange(s.code)))).filter(Boolean) as
        { first: string; last: string }[];
      if (!ranges.length) { if (!cancelled) { setRows([]); setStatus("ready"); } return; }
      const end = new Date(Math.max(...ranges.map((r) => +new Date(r.last))));
      let start = new Date(Math.min(...ranges.map((r) => +new Date(r.first))));
      if (agg === "raw") start = new Date(Math.max(+start, +end - RAW_WINDOW_DAYS * 86400000));
      const day = (d: Date) => d.toISOString().slice(0, 10);

      const results = await Promise.all(
        sensors.map((s) =>
          fetchStationSeries({ code: s.code, variable, agg, value, start: day(start), end: day(end) }),
        ),
      );
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
    })().catch((err) => {
      if (cancelled) return;
      // 403 = this value flavour is hidden by the dataset page.
      setStatus(err?.response?.status === 403 ? "hidden" : "error");
    });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, variable, agg, value]);

  const series = useMemo(
    () => sensors.map((s) => ({
      field: s.exposure ?? s.code,
      color: COLORS[s.exposure ?? "other"],
      label: s.exposure ? t[s.exposure] : s.code,
    })),
    [sensors, t],
  );

  const formatTick = (iso: string) =>
    new Date(iso).toLocaleDateString(language, agg === "raw"
      ? { day: "2-digit", month: "short", hour: "2-digit" }
      : { day: "2-digit", month: "short" });

  return (
    <div className="p-3" style={{ fontSize: 12 }}>
      <div className="font-semibold text-gray-800">{sensors[0]?.site ?? sensors[0]?.name}</div>
      <div className="text-gray-500 mb-2">
        {sensors[0]?.commune ? `${sensors[0].commune} · ` : ""}
        {meta ? `${meta[language]} (${meta.unit})` : variable}
      </div>

      {status === "loading" && <p className="text-gray-500">{t.loading}</p>}
      {status === "error" && <p className="text-red-600">{t.error}</p>}
      {status === "hidden" && <p className="text-gray-500">{t.hidden}</p>}
      {status === "ready" && rows.length === 0 && <p className="text-gray-500">{t.empty}</p>}

      {status === "ready" && rows.length > 0 && (
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <LineChart data={rows} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="period" tickFormatter={formatTick} minTickGap={32} fontSize={10} />
              <YAxis fontSize={10} domain={["auto", "auto"]} />
              <Tooltip
                labelFormatter={(l) => new Date(String(l)).toLocaleString(language)}
                formatter={(v: number) => [`${Number(v).toFixed(1)} ${meta?.unit ?? ""}`]}
              />
              <Legend />
              {series.map((s) => (
                <Line key={s.field} dataKey={s.field} name={s.label} stroke={s.color}
                      dot={false} strokeWidth={1.5} connectNulls isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
