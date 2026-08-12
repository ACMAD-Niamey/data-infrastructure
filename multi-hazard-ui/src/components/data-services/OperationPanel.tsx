import { catalogBaseUrl } from '../../config/api';
import type { OpenApiOperation } from '../../types/openApiSchema';
import { CodeSampleTabs } from './CodeSampleTabs';

const METHOD_BADGE: Record<string, string> = {
  GET: 'bg-hub-100 text-hub-700',
  POST: 'bg-amber-100 text-amber-700',
  PUT: 'bg-purple-100 text-purple-700',
  PATCH: 'bg-purple-100 text-purple-700',
  DELETE: 'bg-red-100 text-red-700',
};

function placeholderUrl(operation: OpenApiOperation): string {
  const pathWithPlaceholders = operation.path.replace(/\{([^}]+)\}/g, (_match, name) => `<${name}>`);
  const queryParams = operation.parameters.filter((p) => p.in === 'query');
  if (queryParams.length === 0) return `${catalogBaseUrl}${pathWithPlaceholders}`;
  const query = queryParams.map((p) => `${p.name}=<${p.name}>`).join('&');
  return `${catalogBaseUrl}${pathWithPlaceholders}?${query}`;
}

export function OperationPanel({ operation }: { operation: OpenApiOperation }) {
  const url = placeholderUrl(operation);

  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded ${METHOD_BADGE[operation.method] ?? 'bg-gray-100 text-gray-700'}`}>
            {operation.method}
          </span>
          <code className="text-sm text-gray-800 font-mono">{operation.path}</code>
        </div>
        {operation.summary && <h2 className="text-lg font-bold text-gray-900">{operation.summary}</h2>}
        {operation.description && (
          <p className="text-sm text-gray-600 mt-1.5 leading-relaxed">{operation.description}</p>
        )}
      </div>

      {operation.parameters.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Parameters</p>
          <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2 font-semibold text-gray-600">Name</th>
                <th className="text-left px-3 py-2 font-semibold text-gray-600">In</th>
                <th className="text-left px-3 py-2 font-semibold text-gray-600">Required</th>
                <th className="text-left px-3 py-2 font-semibold text-gray-600">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {operation.parameters.map((p) => (
                <tr key={`${p.in}:${p.name}`}>
                  <td className="px-3 py-2 font-mono text-xs text-gray-800">{p.name}</td>
                  <td className="px-3 py-2 text-gray-500">{p.in}</td>
                  <td className="px-3 py-2 text-gray-500">{p.required ? 'Yes' : 'No'}</td>
                  <td className="px-3 py-2 text-gray-600">{p.description || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CodeSampleTabs request={{ method: operation.method, url }} label="Example request" />
    </div>
  );
}
