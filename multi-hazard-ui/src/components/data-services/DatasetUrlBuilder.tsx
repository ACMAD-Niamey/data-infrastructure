import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { useDataPlatformCatalog } from '../../hooks/useDataPlatformCatalog';
import { fetchDatasetAvailability, fetchDatasetVisualization } from '../../services/layersApi';
import { availabilityEndpointUrl, notebookUrl, stacCollectionUrl, visualizationEndpointUrl } from '../../lib/datasetUrls';
import type { CatalogLayer } from '../../types/catalogLayer';
import { CodeSampleTabs } from './CodeSampleTabs';

export function DatasetUrlBuilder() {
  const { layers, loading, error } = useDataPlatformCatalog();
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<CatalogLayer | null>(null);

  const [dates, setDates] = useState<string[]>([]);
  const [date, setDate] = useState<string | null>(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);

  const [tileUrl, setTileUrl] = useState<string | null>(null);
  const [tileLoading, setTileLoading] = useState(false);

  const filtered = search
    ? layers.filter((l) => l.title.toLowerCase().includes(search.toLowerCase()))
    : layers;

  // Load available dates whenever the selected dataset changes.
  useEffect(() => {
    if (!selected) {
      setDates([]);
      setDate(null);
      return;
    }
    let cancelled = false;
    setAvailabilityLoading(true);
    setDates([]);
    setDate(null);
    fetchDatasetAvailability({ datasetId: selected.dataset.id, cadence: selected.dataset.cadence })
      .then(({ options, max }) => {
        if (cancelled) return;
        setDates(options.map((o) => o.value));
        setDate(max || options[0]?.value || null);
      })
      .catch(() => {
        if (!cancelled) {
          setDates([]);
          setDate(null);
        }
      })
      .finally(() => {
        if (!cancelled) setAvailabilityLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  // Resolve the actual tile URL whenever the selected date changes.
  useEffect(() => {
    if (!selected || !date) {
      setTileUrl(null);
      return;
    }
    let cancelled = false;
    setTileLoading(true);
    fetchDatasetVisualization({ datasetId: selected.dataset.id, cadence: selected.dataset.cadence, date })
      .then(({ tileUrl: resolved }) => {
        if (!cancelled) setTileUrl(resolved);
      })
      .catch(() => {
        if (!cancelled) setTileUrl(null);
      })
      .finally(() => {
        if (!cancelled) setTileLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected, date]);

  const visualizationEndpoint = selected && date
    ? visualizationEndpointUrl(selected.dataset.id, selected.dataset.cadence, date)
    : null;
  const availabilityEndpoint = selected
    ? availabilityEndpointUrl(selected.dataset.id, selected.dataset.cadence)
    : null;
  const stacUrl = selected?.details?.has_stac_collection
    ? stacCollectionUrl(selected.dataset.stac_collection)
    : null;
  const notebookEndpoint = selected?.details?.has_notebook
    ? notebookUrl(selected.dataset.id)
    : null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-1">Dataset URL builder</h2>
        <p className="text-sm text-gray-600">
          Pick a dataset to get its ready-to-use API URLs — no API key required.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Dataset picker */}
        <div>
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search datasets..."
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-hub-400"
            />
          </div>

          {loading && <p className="text-sm text-gray-500">Loading datasets…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="border border-gray-200 rounded-lg max-h-80 overflow-y-auto divide-y divide-gray-100">
            {filtered.map((layer) => (
              <button
                key={layer.dataset.id}
                type="button"
                onClick={() => setSelected(layer)}
                className={`w-full text-left px-3.5 py-2.5 text-sm transition-colors ${
                  selected?.dataset.id === layer.dataset.id ? 'bg-hub-100 text-hub-800' : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                <div className="font-medium">{layer.title}</div>
                <div className="text-xs text-gray-400">{layer.dataset.cadence}</div>
              </button>
            ))}
            {!loading && filtered.length === 0 && (
              <p className="px-3.5 py-3 text-sm text-gray-400">No datasets match your search.</p>
            )}
          </div>
        </div>

        {/* Date picker */}
        <div>
          {!selected ? (
            <div className="h-full flex items-center justify-center text-sm text-gray-400 border border-dashed border-gray-200 rounded-lg p-6">
              Select a dataset to configure its request.
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Cadence</p>
                <p className="text-sm text-gray-800">{selected.dataset.cadence}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Date</p>
                {availabilityLoading ? (
                  <p className="text-sm text-gray-400">Loading available dates…</p>
                ) : dates.length === 0 ? (
                  <p className="text-sm text-gray-400">No available dates for this dataset.</p>
                ) : (
                  <select
                    value={date ?? ''}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-hub-400"
                  >
                    {dates.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div className="space-y-5 pt-2 border-t border-gray-200">
          {visualizationEndpoint && (
            <CodeSampleTabs
              request={{ method: 'GET', url: visualizationEndpoint }}
              label="Visualization API endpoint"
            />
          )}

          {tileLoading && <p className="text-xs text-gray-400">Resolving tile URL…</p>}
          {tileUrl && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                Resolved tile URL (for map clients)
              </p>
              <pre className="px-3.5 py-3 text-[12px] leading-relaxed text-white/90 font-mono bg-hub-900 rounded-lg overflow-x-auto whitespace-pre-wrap break-all">
                {tileUrl}
              </pre>
            </div>
          )}

          {availabilityEndpoint && (
            <CodeSampleTabs request={{ method: 'GET', url: availabilityEndpoint }} label="Availability endpoint" />
          )}

          {stacUrl && <CodeSampleTabs request={{ method: 'GET', url: stacUrl }} label="STAC collection URL" />}

          {notebookEndpoint && (
            <CodeSampleTabs request={{ method: 'GET', url: notebookEndpoint }} label="Example notebook URL" />
          )}
        </div>
      )}
    </div>
  );
}
