import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, ExternalLink, Code2 } from 'lucide-react';
import NavBar from '../components/NavBar';
import { useDataPlatformCatalog } from '../hooks/useDataPlatformCatalog';
import { useHazardCategories } from '../hooks/useHazardCategories';
import { inferCategory } from '../lib/inferCategory';
import { catalogBaseUrl } from '../config/api';
import { fetchDatasetAvailability } from '../services/layersApi';

const DETAIL_TABS = ['Overview', 'Metadata', 'Methodology', 'Example Notebook'] as const;
type DetailTab = typeof DETAIL_TABS[number];

const BADGE_COLORS: Record<string, string> = {
  drought: 'bg-amber-100 text-amber-700',
  flood: 'bg-blue-100 text-blue-700',
  weather: 'bg-sky-100 text-sky-700',
  heat: 'bg-red-100 text-red-700',
  agriculture: 'bg-green-100 text-green-700',
  exposure: 'bg-purple-100 text-purple-700',
  impact: 'bg-orange-100 text-orange-700',
  boundary: 'bg-gray-100 text-gray-700',
  other: 'bg-gray-100 text-gray-600',
};

export default function DataPlatformDetail() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { layers, loading } = useDataPlatformCatalog();
  const categories = useHazardCategories();
  const [activeTab, setActiveTab] = useState<DetailTab>('Overview');
  const [startDate, setStartDate] = useState<string | null>(null);

  const layer = layers.find((l) => l.dataset.id === datasetId);

  useEffect(() => {
    if (!layer) return;
    setStartDate(null);
    fetchDatasetAvailability({ datasetId: layer.dataset.id, cadence: layer.dataset.cadence })
      .then(({ min }) => setStartDate(min))
      .catch(() => setStartDate(null));
  }, [layer?.dataset.id, layer?.dataset.cadence]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <NavBar />
        <div className="flex-1 flex items-center justify-center text-sm text-gray-500">Loading…</div>
      </div>
    );
  }

  if (!layer) {
    return (
      <div className="min-h-screen flex flex-col">
        <NavBar />
        <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
          <h1 className="text-2xl font-bold text-hub-800 mb-2">Dataset not found</h1>
          <p className="text-gray-500 mb-4">No dataset matches "{datasetId}".</p>
          <Link to="/data-platforms" className="text-hub-700 hover:text-hub-400 text-sm font-medium">
            ← Back to Data Platforms
          </Link>
        </div>
      </div>
    );
  }

  const categoryKey = inferCategory(layer);
  const hazardCat = categories.find((c) => c.key === categoryKey);
  const d = layer.details;

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      <div className="max-w-4xl mx-auto w-full px-6 py-8 flex-1">
        <Link to="/data-platforms" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-hub-700 mb-4">
          <ArrowLeft className="size-4" /> Back to Data Platforms
        </Link>

        <div className="flex items-start justify-between gap-3 mb-1">
          <h1 className="text-2xl font-bold text-hub-800">{layer.title}</h1>
          {hazardCat && (
            <span className={`text-xs font-semibold px-2 py-1 rounded shrink-0 ${BADGE_COLORS[categoryKey] ?? BADGE_COLORS.other}`}>
              {hazardCat.label}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 mb-6">{layer.dataset.title}</p>

        {/* Tabs */}
        <div className="flex gap-0 border-b border-gray-200 mb-6 overflow-x-auto">
          {DETAIL_TABS.map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`text-sm font-medium px-4 py-2.5 border-b-2 whitespace-nowrap transition-colors ${
                activeTab === t
                  ? 'border-hub-400 text-hub-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t}
              {t === 'Example Notebook' && d?.has_notebook && (
                <Code2 className="inline size-3.5 ml-1.5 -mt-0.5" />
              )}
            </button>
          ))}
        </div>

        {activeTab === 'Overview' && (
          <div className="space-y-5">
            <p className="text-sm text-gray-700 leading-relaxed">
              {layer.description?.plain || 'No description available.'}
            </p>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Legend
                {d?.legend_description && (
                  <span className="normal-case font-normal text-[11px] text-gray-400"> — {d.legend_description}</span>
                )}
              </p>
              {layer.legend && Object.keys(layer.legend).length > 0 ? (
                <div className="flex flex-wrap gap-x-5 gap-y-1.5">
                  {Object.entries(layer.legend).map(([label, color]) => (
                    <div key={label} className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full border border-gray-200 shrink-0"
                           style={{ backgroundColor: color as string }} />
                      <span className="text-xs text-gray-700">{label}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400">No legend defined.</p>
              )}
            </div>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link
                to={`/geoportal?dataset=${layer.dataset.id}`}
                className="inline-flex items-center gap-1.5 bg-hub-800 text-white hover:bg-hub-700 rounded px-4 py-2 text-sm font-medium transition-colors"
              >
                Open in Geoportal
              </Link>
              {d?.has_stac_collection && (
                <a
                  href={`${catalogBaseUrl}/stac/collections/${layer.dataset.stac_collection}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 border border-gray-300 text-gray-700 hover:border-hub-400 hover:text-hub-700 rounded px-4 py-2 text-sm font-medium transition-colors"
                >
                  View STAC collection <ExternalLink className="size-3.5" />
                </a>
              )}
            </div>
          </div>
        )}

        {activeTab === 'Metadata' && (
          <table className="w-full text-sm max-w-md">
            <tbody className="divide-y divide-gray-100">
              {[
                ['Category', hazardCat?.label ?? '—'],
                ['Coverage', d?.coverage || 'Africa'],
                ['Resolution', d?.resolution || '—'],
                ['Update frequency', d?.update_frequency || '—'],
                ['Source', d?.source_organization || layer.dataset.title],
                ['Cadence', layer.dataset.cadence],
                ['Start date', startDate || '—'],
                ['STAC collection', layer.dataset.stac_collection],
              ].map(([k, v]) => (
                <tr key={k}>
                  <td className="py-2 text-gray-500 pr-6 whitespace-nowrap w-40">{k}</td>
                  <td className="py-2 text-gray-800 font-medium">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'Methodology' && (
          <div>
            {d?.methodology_html ? (
              <div
                className="text-sm text-gray-700 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: d.methodology_html }}
              />
            ) : (
              <p className="text-sm text-gray-400">No methodology description added yet.</p>
            )}
            {d?.methodology_url && (
              <a
                href={d.methodology_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 mt-4 text-sm font-medium text-hub-700 hover:text-hub-400"
              >
                View full methodology documentation <ExternalLink className="size-3.5" />
              </a>
            )}
          </div>
        )}

        {activeTab === 'Example Notebook' && <NotebookTab datasetId={layer.dataset.id} />}
      </div>
    </div>
  );
}

function NotebookTab({ datasetId }: { datasetId: string }) {
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    axios
      .get(`${catalogBaseUrl}/api/catalog/datasets/${datasetId}/notebook/`)
      .then((r) => {
        if (!cancelled) setHtml(r.data.html);
      })
      .catch(() => {
        if (!cancelled) setHtml(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  if (loading) {
    return <p className="text-sm text-gray-500">Loading notebook…</p>;
  }

  if (!html) {
    return <p className="text-sm text-gray-400">No example notebook available for this dataset yet.</p>;
  }

  return (
    <iframe
      srcDoc={html}
      sandbox="allow-scripts"
      referrerPolicy="no-referrer"
      className="w-full min-h-[600px] border border-gray-200 rounded"
      title="Example notebook"
    />
  );
}
