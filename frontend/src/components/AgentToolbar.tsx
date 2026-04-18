import { useState, useEffect } from 'react';
import { fetchAgentHealth } from '../api/agentApi';
import type { AgentHealthResponse } from '../types/agentTypes';
import '../agents.css';

export type AgentTab = 'scan' | 'score' | 'tailor' | 'batch' | 'tracker' | 'autoapply';

const TABS: { key: AgentTab; icon: string; label: string; color: string }[] = [
  { key: 'scan', icon: '🔍', label: 'Scan', color: '#06b6d4' },
  { key: 'score', icon: '📊', label: 'Score', color: '#10b981' },
  { key: 'tailor', icon: '✂️', label: 'Tailor CV', color: '#d946ef' },
  { key: 'batch', icon: '⚡', label: 'Batch', color: '#f59e0b' },
  { key: 'tracker', icon: '📋', label: 'Tracker', color: '#3b82f6' },
  { key: 'autoapply', icon: '🚀', label: 'Auto Apply', color: '#059669' },
];

interface AgentToolbarProps {
  onTabChange?: (tab: AgentTab) => void;
  activeTab?: AgentTab | null;
}

export default function AgentToolbar({ onTabChange, activeTab: controlledTab }: AgentToolbarProps) {
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
