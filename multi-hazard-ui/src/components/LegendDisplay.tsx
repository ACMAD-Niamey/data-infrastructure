// A layer's legend renders one of two ways depending on its data:
// - Categorical (few entries, text labels like "No Drought") → a swatch list.
// - A sequential numeric ramp (many entries, e.g. 15..200) → a compact gradient
//   strip with just the min/max labels, so it doesn't dominate a small panel.
const RAMP_ENTRY_THRESHOLD = 8;

function isNumericRamp(entries: [string, string][]): boolean {
  return (
    entries.length > RAMP_ENTRY_THRESHOLD &&
    entries.every(([label]) => label.trim() !== '' && !Number.isNaN(Number(label)))
  );
}

type LegendDisplayProps = {
  entries: [string, string][];
};

export function LegendDisplay({ entries }: LegendDisplayProps) {
  if (entries.length === 0) return null;

  if (isNumericRamp(entries)) {
    const sorted = [...entries].sort(([a], [b]) => Number(a) - Number(b));
    const gradient = `linear-gradient(to right, ${sorted.map(([, color]) => color).join(', ')})`;
    return (
      <div>
        <div className="h-3 w-full rounded-full border border-gray-200" style={{ background: gradient }} />
        <div className="flex justify-between text-[10px] text-gray-500 mt-1">
          <span>{sorted[0][0]}</span>
          <span>{sorted[sorted.length - 1][0]}</span>
        </div>
      </div>
    );
  }

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
