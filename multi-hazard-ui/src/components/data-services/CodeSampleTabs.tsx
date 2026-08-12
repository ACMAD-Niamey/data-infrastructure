import { useState } from 'react';
import { CodeBlock } from '../CodeBlock';
import { buildCurlSample, buildFetchSample, buildPythonSample, type SampleRequest } from '../../lib/apiSamples';

const TABS = ['curl', 'JavaScript', 'Python'] as const;
type Tab = typeof TABS[number];

const BUILDERS: Record<Tab, (req: SampleRequest) => string> = {
  curl: buildCurlSample,
  JavaScript: buildFetchSample,
  Python: buildPythonSample,
};

export function CodeSampleTabs({ request, label }: { request: SampleRequest; label?: string }) {
  const [tab, setTab] = useState<Tab>('curl');

  return (
    <div>
      {label && <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{label}</p>}
      <div className="flex gap-0 mb-0">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`text-xs font-medium px-3 py-1.5 rounded-t-md transition-colors ${
              tab === t ? 'bg-hub-900 text-white' : 'bg-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <CodeBlock code={BUILDERS[tab](request)} />
    </div>
  );
}
