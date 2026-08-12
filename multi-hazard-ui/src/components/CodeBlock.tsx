import { useState } from 'react';
import { Check, Copy, X } from 'lucide-react';

type CopyState = 'idle' | 'copied' | 'failed';

export function CodeBlock({ code, label }: { code: string; label?: string }) {
  const [copyState, setCopyState] = useState<CopyState>('idle');

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopyState('copied');
    } catch {
      setCopyState('failed');
    }
    setTimeout(() => setCopyState('idle'), 1800);
  }

  return (
    <div className="relative bg-hub-900 rounded-lg overflow-hidden">
      {label && (
        <div className="px-3.5 py-2 text-xs font-semibold text-white/60 border-b border-white/10">{label}</div>
      )}
      <button
        type="button"
        onClick={handleCopy}
        className="absolute top-2.5 right-2.5 flex items-center gap-1.5 text-[11px] font-medium px-2 py-1 rounded border border-white/20 text-white/70 hover:text-white hover:border-white/40 transition-colors"
      >
        {copyState === 'copied' ? (
          <>
            <Check className="size-3" /> Copied
          </>
        ) : copyState === 'failed' ? (
          <>
            <X className="size-3" /> Couldn't copy
          </>
        ) : (
          <>
            <Copy className="size-3" /> Copy
          </>
        )}
      </button>
      <pre className="px-3.5 py-3 pr-20 text-[12px] leading-relaxed text-white/90 font-mono overflow-x-auto whitespace-pre-wrap break-all">
        {code}
      </pre>
    </div>
  );
}
