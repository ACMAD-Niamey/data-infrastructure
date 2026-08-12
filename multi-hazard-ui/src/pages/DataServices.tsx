import { useState } from 'react';
import { Terminal, ShieldCheck, ExternalLink } from 'lucide-react';
import NavBar from '../components/NavBar';
import { ApiSidebar } from '../components/data-services/ApiSidebar';
import { OperationPanel } from '../components/data-services/OperationPanel';
import { DatasetUrlBuilder } from '../components/data-services/DatasetUrlBuilder';
import { useOpenApiSchema } from '../hooks/useOpenApiSchema';
import { catalogBaseUrl } from '../config/api';
import type { Selection } from '../types/dataServices';

function Overview() {
  return (
    <div className="space-y-5 max-w-2xl">
      <h2 className="text-lg font-bold text-gray-900">Multi-Hazard Hub API</h2>
      <p className="text-sm text-gray-600 leading-relaxed">
        Browse the public catalog, dataset, and station endpoints on the left, or jump straight to the{' '}
        <span className="font-semibold text-hub-700">Dataset URL builder</span> to pick a dataset and get its
        ready-to-use API URLs.
      </p>
      <div className="flex items-start gap-3 bg-hub-100 border border-hub-400/30 rounded-lg px-4 py-3.5">
        <ShieldCheck className="size-5 text-hub-700 shrink-0 mt-0.5" />
        <div className="text-sm text-hub-800">
          <p className="font-semibold mb-0.5">No API key required</p>
          <p className="text-hub-700/80">These endpoints are public — no authentication header is needed today.</p>
        </div>
      </div>
      <a
        href={`${catalogBaseUrl}/api/docs/`}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-hub-700 hover:text-hub-400"
      >
        Full interactive schema (Swagger) <ExternalLink className="size-3.5" />
      </a>
    </div>
  );
}

export default function DataServices() {
  const { groups, loading, error } = useOpenApiSchema();
  const [selected, setSelected] = useState<Selection>({ type: 'overview' });

  const selectedOperation = selected.type === 'operation'
    ? groups
      .flatMap((g) => g.subgroups)
      .flatMap((sg) => sg.operations)
      .find((op) => op.operationId === selected.operationId)
    : null;

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      <section className="relative pt-2 pb-4 px-6 bg-hub-900 text-white">
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{ background: 'linear-gradient(90deg, #33CD33, #F3D545)' }}
        />
        <div className="max-w-6xl mx-auto py-6">
          <div className="flex items-center gap-2 text-hub-400 text-sm font-semibold uppercase tracking-wide mb-3">
            <Terminal className="size-4" /> Data Services
          </div>
          <h1 className="text-3xl font-bold mb-2">Access APIs, data downloads, and programmatic services</h1>
          <p className="text-gray-300 max-w-2xl leading-relaxed">
            Reference for the Multi-Hazard Hub's public API, plus a dataset URL builder to get a ready-to-use
            request for any dataset in the catalog.
          </p>
        </div>
      </section>

      <section className="flex-1 px-6 py-8 bg-white">
        <div className="max-w-6xl mx-auto grid md:grid-cols-[240px_1fr] gap-8">
          <aside className="md:sticky md:top-4 md:self-start">
            {loading && <p className="text-sm text-gray-400 px-3">Loading endpoints…</p>}
            {error && <p className="text-sm text-red-600 px-3">{error}</p>}
            {!loading && !error && <ApiSidebar groups={groups} selected={selected} onSelect={setSelected} />}
          </aside>

          <main>
            {selected.type === 'overview' && <Overview />}
            {selected.type === 'builder' && <DatasetUrlBuilder />}
            {selected.type === 'operation' && selectedOperation && (
              <OperationPanel operation={selectedOperation} />
            )}
            {selected.type === 'operation' && !selectedOperation && !loading && (
              <p className="text-sm text-gray-400">Endpoint not found.</p>
            )}
          </main>
        </div>
      </section>
    </div>
  );
}
