/* ═══════════════════════════════════════════════════════════════
   StartupFiltersBar — 🚀 Startup Filters moved below the search bar
   Horizontal pill-style toggle bar for quick filtering
   ═══════════════════════════════════════════════════════════════ */
import { Filters } from '../types';

interface StartupFiltersBarProps {
  filters: Filters;
  onFilterChange: (f: Filters) => void;
}

const FILTER_PILLS: { key: keyof Filters; label: string; icon: string }[] = [
  { key: 'startup_only', label: 'Startup Only', icon: '🚀' },
  { key: 'stealth_only', label: 'Stealth', icon: '🔒' },
  { key: 'engineering_only', label: 'Engineering', icon: '🔧' },
  { key: 'india_only', label: 'India', icon: '🇮🇳' },
  { key: 'founding_only', label: 'Founding Engineer', icon: '⚡' },
  { key: 'remote_india', label: 'Remote India', icon: '🌍' },
  { key: 'offers_relocation', label: 'Relocation', icon: '✈️' },
];

export default function StartupFiltersBar({ filters, onFilterChange }: StartupFiltersBarProps) {
  const toggle = (key: keyof Filters) => {
    const current = !!filters[key];
    onFilterChange({ ...filters, [key]: current ? undefined : true });
  };

  const activeCount = FILTER_PILLS.filter(p => !!filters[p.key]).length;

  return (
    <div className="startup-filters-bar">
      <div className="sfb-inner">
        <div className="sfb-label">
          <span className="sfb-label-icon">🚀</span>
          <span className="sfb-label-text">Startup Filters</span>
          {activeCount > 0 && (
            <span className="sfb-active-count">{activeCount}</span>
          )}
        </div>
        <div className="sfb-pills">
          {FILTER_PILLS.map(pill => {
            const active = !!filters[pill.key];
            return (
              <button
                key={pill.key}
                className={`sfb-pill ${active ? 'sfb-pill-active' : ''}`}
                onClick={() => toggle(pill.key)}
                title={pill.label}
              >
                <span className="sfb-pill-icon">{pill.icon}</span>
                <span className="sfb-pill-label">{pill.label}</span>
              </button>
            );
          })}
        </div>
        {activeCount > 0 && (
          <button
            className="sfb-clear"
            onClick={() => {
              const cleared = { ...filters };
              FILTER_PILLS.forEach(p => { (cleared as any)[p.key] = undefined; });
              onFilterChange(cleared);
            }}
          >
            Clear all
          </button>
        )}
      </div>
    </div>
  );
}
