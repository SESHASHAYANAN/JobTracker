import { useState, useEffect } from 'react';
import { fetchAgentHealth } from '../api/agentApi';
import type { AgentHealthResponse } from '../types/agentTypes';
import type { Filters } from '../types';
import '../agents.css';

export type AgentTab = 'tailor' | 'tracker';

const TABS: { key: AgentTab; icon: string; label: string; color: string }[] = [
  { key: 'tailor', icon: '✂️', label: 'Tailor CV', color: '#d946ef' },
  { key: 'tracker', icon: '📋', label: 'Tracker', color: '#3b82f6' },
];

const FILTER_PILLS: { key: keyof Filters; label: string; icon: string; color: string }[] = [
  { key: 'startup_only', label: 'Startup Only', icon: '🚀', color: '#f97316' },
  { key: 'stealth_only', label: 'Stealth Only', icon: '🔒', color: '#8b5cf6' },
  { key: 'engineering_only', label: 'Engineering Only', icon: '🔧', color: '#06b6d4' },
  { key: 'india_only', label: 'India Only', icon: '🇮🇳', color: '#10b981' },
  { key: 'founding_only', label: 'Founding Engineer', icon: '⚡', color: '#eab308' },
  { key: 'remote_india', label: 'Remote India', icon: '🌍', color: '#3b82f6' },
  { key: 'offers_relocation', label: 'Offers Relocation', icon: '✈️', color: '#ec4899' },
];

interface AgentToolbarProps {
  onTabChange?: (tab: AgentTab) => void;
  activeTab?: AgentTab | null;
  filters?: Filters;
  onFilterChange?: (f: Filters) => void;
}

export default function AgentToolbar({ onTabChange, activeTab: controlledTab, filters, onFilterChange }: AgentToolbarProps) {
  const [health, setHealth] = useState<AgentHealthResponse | null>(null);

  useEffect(() => {
    fetchAgentHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'error', warnings: ['Backend unreachable'], cv_loaded: false, data_dir: '' }));
  }, []);

  const handleClick = (tab: AgentTab) => {
    if (onTabChange) {
      onTabChange(tab);
    }
  };

  const toggleFilter = (key: keyof Filters) => {
    if (!filters || !onFilterChange) return;
    const current = !!filters[key];
    onFilterChange({ ...filters, [key]: current ? undefined : true });
  };

  const activeFilterCount = filters
    ? FILTER_PILLS.filter(p => !!filters[p.key]).length
    : 0;

  const clearAllFilters = () => {
    if (!filters || !onFilterChange) return;
    const cleared = { ...filters };
    FILTER_PILLS.forEach(p => { (cleared as any)[p.key] = undefined; });
    onFilterChange(cleared);
  };

  return (
    <div className="agent-toolbar-wrapper">
      {/* Compact Toolbar Row */}
      <div className="agent-toolbar">
        <div className="agent-toolbar-left">
          <div className="agent-toolbar-badge">
            <span className="agent-toolbar-badge-icon">AI</span>
            <span className="agent-toolbar-badge-label">Agent Suite</span>
          </div>

          {/* Health indicator */}
          {health && (
            <div className={`agent-toolbar-health ${health.status === 'ok' ? 'health-ok' : 'health-warn'}`}>
              <span className={`agent-toolbar-dot ${health.status === 'ok' ? 'dot-ok' : 'dot-warn'}`} />
              {health.status === 'ok' ? 'Connected' : 'Degraded'}
            </div>
          )}

          {health && (
            <div className={`agent-toolbar-health ${health.cv_loaded ? 'health-cv' : 'health-nocv'}`}>
              📄 {health.cv_loaded ? 'CV Loaded' : 'No CV'}
            </div>
          )}

          {/* ── Filter Pills — inline after Agent Suite ── */}
          {filters && onFilterChange && (
            <div className="agent-filter-pills">
              <span className="agent-filter-divider" />
              {FILTER_PILLS.map(pill => {
                const active = !!filters[pill.key];
                return (
                  <button
                    key={pill.key}
                    className={`agent-filter-pill ${active ? 'agent-filter-pill-active' : ''}`}
                    onClick={() => toggleFilter(pill.key)}
                    title={pill.label}
                    style={{
                      '--pill-color': pill.color,
                    } as React.CSSProperties}
                  >
                    <span className="agent-filter-pill-icon">{pill.icon}</span>
                    <span className="agent-filter-pill-label">{pill.label}</span>
                  </button>
                );
              })}
              {activeFilterCount > 0 && (
                <button className="agent-filter-clear" onClick={clearAllFilters} title="Clear all filters">
                  ✕ Clear ({activeFilterCount})
                </button>
              )}
            </div>
          )}
        </div>

        {/* Agent Tab Buttons */}
        <div className="agent-toolbar-tabs">
          {TABS.map(tab => (
            <button
              key={tab.key}
              className={`agent-toolbar-tab ${controlledTab === tab.key ? 'agent-tab-active-inline' : ''}`}
              onClick={() => handleClick(tab.key)}
              style={{
                '--tab-color': tab.color,
              } as React.CSSProperties}
              title={tab.label}
            >
              <span className="agent-toolbar-tab-icon">{tab.icon}</span>
              <span className="agent-toolbar-tab-label">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
