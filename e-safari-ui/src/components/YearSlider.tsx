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
  const range = max > min ? max - min : 1;

  return (
    <div style={{ position: 'relative', height: 40, width: '100%' }}>
      {/* Background track */}
      <div style={{
        position: 'absolute',
        top: 8,
        left: 0,
        right: 0,
        height: 2,
        borderRadius: 1,
        backgroundColor: '#bbf7d0',
      }} />
      {/* Active fill */}
      <div style={{
        position: 'absolute',
        top: 8,
        left: 0,
        width: `${((current - min) / range) * 100}%`,
        height: 2,
        borderRadius: 1,
        backgroundColor: '#15803d',
      }} />
      {/* Year dots + labels */}
      {years.map((y) => {
        const pct = ((y - min) / range) * 100;
        const isSelected = y === current;
        return (
          <div
            key={y}
            onClick={() => onChange(String(y))}
            style={{
              position: 'absolute',
              left: `${pct}%`,
              top: 0,
              transform: 'translateX(-50%)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              cursor: 'pointer',
            }}
          >
            {/* Fixed 16×16 area keeps all labels at the same vertical position */}
            <div style={{ width: 16, height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{
                width: isSelected ? 14 : 9,
                height: isSelected ? 14 : 9,
                borderRadius: '50%',
                backgroundColor: isSelected ? 'white' : '#15803d',
                border: isSelected ? '2.5px solid #15803d' : 'none',
                flexShrink: 0,
              }} />
            </div>
            <span style={{
              fontSize: '10px',
              color: isSelected ? '#15803d' : '#9ca3af',
              fontWeight: isSelected ? 600 : 400,
              marginTop: 2,
              whiteSpace: 'nowrap',
              userSelect: 'none',
            }}>
              {y}
            </span>
          </div>
        );
      })}
    </div>
  );
}
