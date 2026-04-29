import { useCallback, useEffect, useState } from "react";
import { fetchFacets, fetchStationList } from "./api/stations";
import type { SpatialExtent, StationFacetsResponse, StationListItem } from "./api/types";
import { StationMap } from "./components/StationMap";
import { StationPanel } from "./components/StationPanel";

export default function App() {
  const [stations, setStations] = useState<StationListItem[]>([]);
  const [extent, setExtent] = useState<SpatialExtent | null>(null);
  const [facets, setFacets] = useState<StationFacetsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [country, setCountry] = useState("");
  const [admin1, setAdmin1] = useState("");
  const [admin2, setAdmin2] = useState("");

  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  useEffect(() => {
    fetchFacets()
      .then(setFacets)
      .catch(() => setFacets({ countries: [], admin1: [], admin2: [] }));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setListError(null);
    fetchStationList({
      country_code: country || undefined,
      admin1: admin1 || undefined,
      admin2: admin2 || undefined,
    })
      .then((res) => {
        if (!cancelled) {
          setStations(res.results);
          setExtent(res.extent);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setListError(e.message ?? "Failed to load stations");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [country, admin1, admin2]);

  const onSelectStation = useCallback((code: string) => {
    setSelectedCode(code);
  }, []);

  const onClosePanel = useCallback(() => setSelectedCode(null), []);

  return (
    <div className="flex h-dvh flex-col bg-slate-950 text-slate-50">
      <header className="flex flex-shrink-0 flex-wrap items-center gap-3 border-b border-slate-800 px-4 py-3">
        <div className="flex flex-col">
          <span className="text-lg font-semibold tracking-tight text-cyan-400">Afri-Met</span>
          <span className="text-xs text-slate-400">Station observations explorer</span>
        </div>

        <div className="flex flex-1 flex-wrap items-end gap-2 md:justify-end">
          <FilterSelect
            label="Country"
            value={country}
            options={facets?.countries ?? []}
            onChange={(v) => {
              setCountry(v);
              setAdmin1("");
              setAdmin2("");
            }}
          />
          <FilterSelect
            label="Region (admin1)"
            value={admin1}
            options={facets?.admin1 ?? []}
            onChange={(v) => {
              setAdmin1(v);
              setAdmin2("");
            }}
          />
          <FilterSelect
            label="District (admin2)"
            value={admin2}
            options={facets?.admin2 ?? []}
            onChange={setAdmin2}
          />
        </div>
      </header>

      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col md:flex-row">
        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
          {loading && (
            <div className="absolute left-4 top-4 z-10 rounded-md bg-slate-900/80 px-3 py-1 text-xs text-slate-300">
              Loading stations…
            </div>
          )}
          {listError && (
            <div className="absolute left-4 top-12 z-10 max-w-md rounded-md bg-red-950/90 px-3 py-2 text-xs text-red-200">
              {listError}
              <span className="mt-1 block text-slate-400">
                Ensure Django is running and Vite proxies /api (see README).
              </span>
            </div>
          )}
          <StationMap stations={stations} extent={extent} onSelectStation={onSelectStation} />
        </div>

        {selectedCode && (
          <>
            <button
              type="button"
              className="fixed inset-0 z-40 bg-black/40 md:hidden"
              aria-label="Close panel"
              onClick={onClosePanel}
            />
            <aside className="fixed inset-x-0 bottom-0 z-50 max-h-[88vh] overflow-y-auto rounded-t-2xl border border-slate-800 bg-white p-4 text-slate-900 md:relative md:inset-auto md:z-0 md:flex md:h-full md:max-h-none md:w-[22rem] md:max-w-none md:rounded-none md:border-l md:border-t-0 md:p-4">
              <StationPanel stationCode={selectedCode} onClose={onClosePanel} />
            </aside>
          </>
        )}
      </div>

      <footer className="flex-shrink-0 border-t border-slate-800 px-4 py-2 text-[11px] text-slate-500">
        {stations.length} station{stations.length === 1 ? "" : "s"} in view · Tap a point for time series
      </footer>
    </div>
  );
}

function FilterSelect(props: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex min-w-[140px] flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">
      {props.label}
      <select
        className="min-h-[44px] rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-slate-100"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      >
        <option value="">All</option>
        {props.options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
