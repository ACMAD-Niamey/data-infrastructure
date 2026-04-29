import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchCountryBounds, fetchFacets, fetchStationList } from "./api/stations";
import type { CountryBoundsOption, SelectOption, SpatialExtent, StationFacetsResponse, StationListItem } from "./api/types";
import { StationMap, type StationLegendMode } from "./components/StationMap";
import { StationPanel } from "./components/StationPanel";

export default function App() {
  const [stations, setStations] = useState<StationListItem[]>([]);
  const [extent, setExtent] = useState<SpatialExtent | null>(null);
  const [facets, setFacets] = useState<StationFacetsResponse | null>(null);
  const [countryBounds, setCountryBounds] = useState<CountryBoundsOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [country, setCountry] = useState("");
  const [admin1, setAdmin1] = useState("");

  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const observedStationCodes = useMemo(() => stations.map((s) => s.station_code), [stations]);
  const countryOptions = useMemo<SelectOption[]>(
    () => [...countryBounds].sort((a, b) => a.label.localeCompare(b.label)),
    [countryBounds],
  );
  const admin1Options = useMemo<SelectOption[]>(
    () => (facets?.admin1 ?? []).map((v) => ({ value: v, label: v })),
    [facets],
  );
  const [showObserved, setShowObserved] = useState(true);
  const [showNoObservation, setShowNoObservation] = useState(true);
  const [legendMode, setLegendMode] = useState<StationLegendMode>("hide");

  useEffect(() => {
    fetchCountryBounds()
      .then(setCountryBounds)
      .catch(() => setCountryBounds([]));
  }, []);

  useEffect(() => {
    fetchFacets(country || undefined)
      .then(setFacets)
      .catch(() => setFacets({ countries: [], admin1: [] }));
  }, [country]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setListError(null);
    fetchStationList({
      country_code: country || undefined,
      admin1: admin1 || undefined,
    })
      .then((res) => {
        if (!cancelled) {
          setStations(res.results);
          if (!country) setExtent(res.extent);
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
  }, [country, admin1]);

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
            options={countryOptions}
            onChange={(v) => {
              setCountry(v);
              setAdmin1("");
              const selected = countryBounds.find((c) => c.value === v);
              if (selected) setExtent(selected.bounds);
            }}
          />
          <FilterSelect
            label="Region (admin1)"
            value={admin1}
            options={admin1Options}
            disabled={!country}
            placeholder={country ? "All" : "Select country first"}
            onChange={setAdmin1}
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
          <StationMap
            extent={extent}
            observedStationCodes={observedStationCodes}
            showObserved={showObserved}
            showNoObservation={showNoObservation}
            legendMode={legendMode}
            onSelectStation={onSelectStation}
          />
          <div className="absolute bottom-4 left-4 z-10 rounded-md border border-slate-700 bg-slate-950/85 p-2 text-xs text-slate-200">
            <div className="mb-1 font-medium text-slate-300">Stations</div>
            <div className="mb-2 flex gap-1">
              <button
                type="button"
                onClick={() => setLegendMode("hide")}
                className={`rounded px-2 py-1 ${legendMode === "hide" ? "bg-slate-700 text-white" : "bg-slate-900/70 text-slate-300"}`}
              >
                Hide
              </button>
              <button
                type="button"
                onClick={() => setLegendMode("dim")}
                className={`rounded px-2 py-1 ${legendMode === "dim" ? "bg-slate-700 text-white" : "bg-slate-900/70 text-slate-300"}`}
              >
                Dim
              </button>
            </div>
            <button
              type="button"
              onClick={() => setShowObserved((v) => !v)}
              className={`flex w-full items-center gap-2 rounded px-1 py-1 text-left ${showObserved ? "opacity-100" : "opacity-50"}`}
            >
              <span className="inline-block h-3 w-3 rounded-full border border-slate-900 bg-green-500" />
              <span>Has observations</span>
            </button>
            <button
              type="button"
              onClick={() => setShowNoObservation((v) => !v)}
              className={`mt-1 flex w-full items-center gap-2 rounded px-1 py-1 text-left ${showNoObservation ? "opacity-100" : "opacity-50"}`}
            >
              <span className="inline-block h-2 w-2 rounded-full border border-slate-900 bg-slate-500" />
              <span>No observations</span>
            </button>
          </div>
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
              <StationPanel
                stationCode={selectedCode}
                onClose={onClosePanel}
                observedStationCodes={observedStationCodes}
              />
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
  options: SelectOption[];
  disabled?: boolean;
  placeholder?: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex min-w-[140px] flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">
      {props.label}
      <select
        className="min-h-[44px] rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-slate-100"
        value={props.value}
        disabled={props.disabled}
        onChange={(e) => props.onChange(e.target.value)}
      >
        <option value="">{props.placeholder ?? "All"}</option>
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
