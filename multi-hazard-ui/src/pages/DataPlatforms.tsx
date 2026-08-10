import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Database, Satellite, BookOpen, Layers } from 'lucide-react';
import NavBar from '../components/NavBar';
import { useDataPlatformCatalog } from '../hooks/useDataPlatformCatalog';
import { useHazardCategories } from '../hooks/useHazardCategories';
import { inferCategory } from '../lib/inferCategory';
import { fetchProjectConfig, getProjectSlug, type ProjectConfig } from '../services/catalogLayersApi';
import type { CatalogLayer } from '../types/catalogLayer';

// Fallback copy shown until (or if) a content editor sets these fields in
// the CMS (ProjectPage "Data Platforms page" panel).
const DEFAULT_TITLE = 'The ACMAD Multi-Hazard Data Infrastructure';
const DEFAULT_DESCRIPTION =
  'A STAC-catalogued archive of satellite, model, and station-derived geospatial datasets ' +
  'covering Africa — drought, flood, weather, heat, and agriculture indicators, ingested on ' +
  'daily, dekadal, and monthly cadences and served as cloud-optimized rasters. Browse the ' +
  'catalog below; each dataset includes metadata, methodology, and an example notebook ' +
  'showing how to access the data programmatically via STAC.';

export default function DataPlatforms() {
  const { layers, loading, error } = useDataPlatformCatalog();
  const categories = useHazardCategories();
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [config, setConfig] = useState<ProjectConfig | null>(null);

  useEffect(() => {
    fetchProjectConfig(getProjectSlug())
      .then(setConfig)
      .catch(() => setConfig(null)); // fine — falls back to default copy below
  }, []);

  const filtered = useMemo(() => {
    return layers.filter((layer) => {
      const matchesCategory = activeCategory === 'all' || inferCategory(layer) === activeCategory;
      const matchesSearch = !search || layer.title.toLowerCase().includes(search.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [layers, search, activeCategory]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    layers.forEach((layer) => {
      const key = inferCategory(layer);
      counts[key] = (counts[key] ?? 0) + 1;
    });
    return counts;
  }, [layers]);

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      {/* Overview */}
      <section className="relative pt-2 pb-4 px-6 bg-hub-900 text-white">
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{ background: 'linear-gradient(90deg, #33CD33, #F3D545)' }}
        />
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-start gap-10">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-hub-400 text-sm font-semibold uppercase tracking-wide mb-3">
              <Database className="size-4" /> Data Platforms
            </div>
            <h1 className="text-3xl font-bold mb-4">{config?.data_platforms_title || DEFAULT_TITLE}</h1>
            <p className="text-gray-300 max-w-3xl leading-relaxed mb-2">
              {config?.data_platforms_description || DEFAULT_DESCRIPTION}
            </p>
            <div className="grid grid-cols-3 gap-4 max-w-md">
              <div>
                <p className="text-2xl font-bold">{layers.length}</p>
                <p className="text-xs text-gray-400">Datasets</p>
              </div>
              <div>
                <p className="text-2xl font-bold">{Object.keys(categoryCounts).length}</p>
                <p className="text-xs text-gray-400">Categories</p>
              </div>
              <div>
                <p className="text-2xl font-bold">{layers.filter((l) => l.details?.has_notebook).length}</p>
                <p className="text-xs text-gray-400">With notebooks</p>
              </div>
            </div>
          </div>
          {config?.data_platforms_image_url && (
            <img
              src={config.data_platforms_image_url}
              alt=""
              className="w-full md:w-72 shrink-0 rounded-lg object-cover max-h-64 md:max-h-80"
            />
          )}
        </div>
      </section>

      {/* Catalog */}
      <section className="py-12 px-6 bg-white flex-1">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search datasets..."
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-hub-400"
              />
            </div>
            <select
              value={activeCategory}
              onChange={(e) => setActiveCategory(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-hub-400"
            >
              <option value="all">All categories</option>
              {categories.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.label} ({categoryCounts[c.key] ?? 0})
                </option>
              ))}
            </select>
          </div>

          {loading && <p className="text-sm text-gray-500">Loading datasets…</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}

          {!loading && !error && filtered.length === 0 && (
            <p className="text-sm text-gray-500">No datasets match your search.</p>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map((layer) => (
              <DatasetCard key={layer.dataset.id} layer={layer} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function DatasetCard({ layer }: { layer: CatalogLayer }) {
  return (
    <Link
      to={`/data-platforms/${layer.dataset.id}`}
      className="border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-hub-400 transition-all group flex flex-col"
    >
      <div className="flex items-center justify-between mb-3">
        <Satellite className="size-6 text-hub-400" />
        {layer.details?.has_notebook && (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-hub-700 bg-hub-100 px-2 py-0.5 rounded">
            <BookOpen className="size-3" /> Notebook
          </span>
        )}
      </div>
      <h3 className="font-bold text-gray-800 mb-1 group-hover:text-hub-700">{layer.title}</h3>
      <p className="text-sm text-gray-500 mb-3 line-clamp-2 flex-1">
        {layer.description.plain || 'No description available.'}
      </p>
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <Layers className="size-3.5" /> {layer.dataset.cadence}
      </div>
    </Link>
  );
}
