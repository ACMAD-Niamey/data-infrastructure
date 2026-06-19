import type { LayerSelectOption } from '../types/catalogLayer';

interface YearSliderProps {
  options: LayerSelectOption[];
  value: string | undefined;
  onChange: (year: string) => void;
}

export function YearSlider({ options, value, onChange }: YearSliderProps) {
  if (options.length === 0) return null;

  const years = options.map((o) => Number(o.value)).sort((a, b) => a - b);
  const min = years[0];
  const max = years[years.length - 1];
  const current = value ? Number(value) : max;

  const listId = `year-ticks-${min}-${max}`;

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#15803d', marginBottom: '2px' }}>
        <span>{current}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={1}
        value={current}
        list={listId}
        onChange={(e) => {
          const v = String(e.target.value);
          // snap to nearest available year
          const nearest = years.reduce((prev, curr) =>
            Math.abs(curr - Number(v)) < Math.abs(prev - Number(v)) ? curr : prev,
          );
          onChange(String(nearest));
        }}
        className="layer-slider"
      />
      <datalist id={listId}>
        {years.map((y) => (
          <option key={y} value={y} />
        ))}
      </datalist>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#6b7280', marginTop: '2px' }}>
        {years.map((y) => (
          <span key={y}>{y}</span>
        ))}
      </div>
    </div>
  );
}
