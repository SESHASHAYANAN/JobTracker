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
