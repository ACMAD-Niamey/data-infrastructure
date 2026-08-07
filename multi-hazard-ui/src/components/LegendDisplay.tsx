import { useState } from 'react';

// A layer's legend renders one of two ways depending on its data:
// - Categorical (few entries, text labels like "No Drought") → always a dotted swatch list.
// - A sequential numeric ramp (many entries, e.g. 15..200) → user picks Strip/Dotted/Vertical,
//   since a plain list of 20 rows dominates a small panel.
const RAMP_ENTRY_THRESHOLD = 8;

type LegendEntry = [string, string];
type LegendMode = 'strip' | 'dotted' | 'vertical';

function isNumericRamp(entries: LegendEntry[]): boolean {
  return (
    entries.length > RAMP_ENTRY_THRESHOLD &&
    entries.every(([label]) => label.trim() !== '' && !Number.isNaN(Number(label)))
  );
}

function DottedList({ entries }: { entries: LegendEntry[] }) {
  return (
    <div className="space-y-1.5">
      {entries.map(([label, color]) => (
        <div key={label} className="flex items-center gap-2">
          <div className="size-4 rounded-full border border-gray-300 shrink-0" style={{ backgroundColor: color }} />
          <span className="text-xs text-gray-700">{label}</span>
        </div>
      ))}
    </div>
  );
}

// Horizontal gradient bar with a label under every color stop. Labels are set in
// vertical writing mode so they stack in a narrow column instead of overlapping
// their neighbors — the only way to fit a number per stop regardless of count.
function StripLegend({ entries }: { entries: LegendEntry[] }) {
  const gradient = `linear-gradient(to right, ${entries.map(([, color]) => color).join(', ')})`;
  return (
    <div>
      <div className="h-3 w-full rounded-full border border-gray-200" style={{ background: gradient }} />
      <div className="flex mt-1">
        {entries.map(([label]) => (
          <span
            key={label}
            className="flex-1 text-[8px] text-gray-500 text-center leading-none"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: 20 }}
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

// Compact vertical bar (bottom = lowest value) — a fixed short height regardless
// of how many stops there are, so it never grows into a tall list.
function VerticalLegend({ entries }: { entries: LegendEntry[] }) {
  const height = 90;
  const gradient = `linear-gradient(to top, ${entries.map(([, color]) => color).join(', ')})`;
  return (
    <div className="flex items-center gap-2">
      <div className="w-3 rounded-full border border-gray-200 shrink-0" style={{ height, background: gradient }} />
      <div className="flex flex-col justify-between text-[10px] text-gray-500" style={{ height }}>
        <span>{entries[entries.length - 1][0]}</span>
        <span>{entries[0][0]}</span>
      </div>
    </div>
  );
}

type LegendDisplayProps = {
  entries: LegendEntry[];
};

export function LegendDisplay({ entries }: LegendDisplayProps) {
  const [mode, setMode] = useState<LegendMode>('strip');

  if (entries.length === 0) return null;
  if (!isNumericRamp(entries)) return <DottedList entries={entries} />;

  const sorted = [...entries].sort(([a], [b]) => Number(a) - Number(b));

  return (
    <div>
      <div className="flex justify-end mb-1">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as LegendMode)}
          className="text-[10px] border border-gray-200 rounded px-1 py-0.5 text-gray-600 bg-white"
        >
          <option value="strip">Strip</option>
          <option value="dotted">Dotted</option>
          <option value="vertical">Vertical</option>
        </select>
      </div>
      {mode === 'strip' && <StripLegend entries={sorted} />}
      {mode === 'dotted' && <DottedList entries={sorted} />}
      {mode === 'vertical' && <VerticalLegend entries={sorted} />}
    </div>
  );
}
