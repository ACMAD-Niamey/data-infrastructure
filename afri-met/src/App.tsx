import { useCallback, useEffect, useId, useMemo, useState } from "react";
import { fetchCountryBounds } from "./api/stations";
import type { CountryBoundsOption, SelectOption } from "./api/types";
import { StationMap } from "./components/StationMap";
import { StationPanel } from "./components/StationPanel";
import acmadLogo from "./assets/acmadLogo.svg";

export default function App() {
  const [countryBounds, setCountryBounds] = useState<CountryBoundsOption[]>([]);
  const [loadingBounds, setLoadingBounds] = useState(true);
  const [boundsError, setBoundsError] = useState<string | null>(null);

  const [country, setCountry] = useState("");

  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const countryOptions = useMemo<SelectOption[]>(
    () => [...countryBounds].sort((a, b) => a.label.localeCompare(b.label)),
    [countryBounds],
  );
  const selectedCountryBounds = useMemo(
    () => countryBounds.find((c) => c.value === country)?.bounds ?? null,
    [countryBounds, country],
  );

  useEffect(() => {
    setLoadingBounds(true);
    setBoundsError(null);
    fetchCountryBounds()
      .then(setCountryBounds)
      .catch((e: Error) => {
        setCountryBounds([]);
        setBoundsError(e.message ?? "Failed to load country bounds");
      })
      .finally(() => setLoadingBounds(false));
  }, []);

  const onSelectStation = useCallback((code: string) => {
    setSelectedCode(code);
  }, []);

  const onClosePanel = useCallback(() => setSelectedCode(null), []);

  return (
    <div className="flex h-dvh flex-col bg-slate-950 text-slate-50">
      <header className="flex flex-shrink-0 flex-wrap items-center gap-3 border-b border-slate-800 px-4 py-3">
        <div className="flex flex-col">
          <span className="text-lg font-semibold tracking-tight text-cyan-400">Afri-Met</span>
          <span className="text-xs text-slate-400">WIS 2.0 Station observations explorer </span>
        </div>
        <div className="ml-auto flex items-center">
          <div className="rounded bg-white p-1.5 shadow-[0_4px_10px_rgba(0,0,0,0.18)]">
            <img src={acmadLogo} alt="ACMAD logo" className="h-9 w-9 object-contain" />
          </div>
        </div>
      </header>
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col md:flex-row">
        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="absolute left-4 top-4 z-10 w-full max-w-xs rounded-md border border-slate-700 bg-slate-950/85 p-2">
            <FilterSelect
              label="Country"
              value={country}
              options={countryOptions}
              onChange={(v) => {
                setCountry(v);
              }}
            />
          </div>
          {loadingBounds && (
            <div className="absolute left-4 top-24 z-10 rounded-md bg-slate-900/80 px-3 py-1 text-xs text-slate-300">
              Loading country bounds…
            </div>
          )}
          {boundsError && (
            <div className="absolute left-4 top-32 z-10 max-w-md rounded-md bg-red-950/90 px-3 py-2 text-xs text-red-200">
              {boundsError}
              <span className="mt-1 block text-slate-400">
                Ensure Django is running and Vite proxies /api.
              </span>
            </div>
          )}
          <StationMap
            extent={selectedCountryBounds}
            countryCode={country || null}
            onSelectStation={onSelectStation}
          />
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
              />
            </aside>
          </>
        )}
      </div>

      <footer className="flex-shrink-0 border-t border-slate-800 px-4 py-2 text-[11px] text-slate-500">TiPG map layer active · Tap a point for time series</footer>
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
  const datalistId = useId();
  const selectedOption = props.options.find((o) => o.value === props.value) ?? null;
  const [query, setQuery] = useState(selectedOption?.label ?? "");

  useEffect(() => {
    const nextLabel = selectedOption?.label ?? "";
    if (query !== nextLabel) setQuery(nextLabel);
  }, [selectedOption?.label]);

  const resolveValue = (raw: string): string | null => {
    const exact = props.options.find((o) => o.label.toLowerCase() === raw.trim().toLowerCase());
    return exact?.value ?? null;
  };

  return (
    <label className="flex w-full flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">
      {props.label}
      <input
        type="text"
        list={datalistId}
        className="min-h-[44px] rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-slate-100"
        value={query}
        disabled={props.disabled}
        placeholder={props.placeholder ?? "All"}
        onChange={(e) => {
          const raw = e.target.value;
          setQuery(raw);
          if (!raw.trim()) {
            props.onChange("");
            return;
          }
          const value = resolveValue(raw);
          if (value) props.onChange(value);
        }}
        onBlur={() => {
          if (!query.trim()) return;
          const value = resolveValue(query);
          if (!value) {
            setQuery(selectedOption?.label ?? "");
          }
        }}
      />
      <datalist id={datalistId}>
        {props.options.map((o) => (
          <option key={o.value} value={o.label} />
        ))}
      </datalist>
    </label>
  );
}
