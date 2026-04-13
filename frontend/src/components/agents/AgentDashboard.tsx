import { useState, useEffect } from 'react';
import { fetchAgentHealth } from '../../api/agentApi';
import type { AgentHealthResponse } from '../../types/agentTypes';
import AgentCard from './AgentCard';
import ScanPanel from './ScanPanel';
import ScorePanel from './ScorePanel';
import TailorPanel from './TailorPanel';
import BatchPanel from './BatchPanel';
import TrackerPanel from './TrackerPanel';
import '../../agents.css';

interface AgentDashboardProps {
  onBackToJobs?: () => void;
}

export default function AgentDashboard({ onBackToJobs }: AgentDashboardProps) {
  const [health, setHealth] = useState<AgentHealthResponse | null>(null);

  useEffect(() => {
    fetchAgentHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'error', warnings: ['Backend unreachable'], cv_loaded: false, data_dir: '' }));
  }, []);

  return (
    <div className="agent-dashboard">
      {/* Header */}
      <header className="ag-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '2rem', height: '2rem', borderRadius: '0.5rem',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.875rem', fontWeight: 700, color: '#fff',
          }}>
            AI
          </div>
          <h1>Agent Suite</h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Health Status */}
          {health && (
            <span className={`ag-header-badge ${health.status === 'ok' ? '' : 'ag-status-error'}`} style={{
              background: health.status === 'ok' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              color: health.status === 'ok' ? '#10b981' : '#f59e0b',
            }}>
              <span className={`ag-pulse ${health.status === 'ok' ? 'ag-pulse-complete' : 'ag-pulse-error'}`} />
              {health.status === 'ok' ? 'Connected' : 'Degraded'}
            </span>
          )}

          {/* CV Status */}
          {health && (
            <span className="ag-header-badge" style={{
              background: health.cv_loaded ? 'rgba(6, 182, 212, 0.15)' : 'rgba(136, 136, 160, 0.15)',
              color: health.cv_loaded ? '#06b6d4' : '#8888a0',
            }}>
              {health.cv_loaded ? '📄 CV Loaded' : '📄 No CV'}
            </span>
          )}

          {/* Back to Jobs */}
          {onBackToJobs && (
            <button
              onClick={onBackToJobs}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
                padding: '0.5rem 1rem',
                borderRadius: '0.5rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                cursor: 'pointer',
                border: '1px solid #3a3a4a',
                background: 'linear-gradient(135deg, #1e1e2e, #2a2a3a)',
                color: '#e4e4eb',
                transition: 'all 0.25s ease',
                fontFamily: "'Inter', system-ui, sans-serif",
              }}
              title="Back to Jobs"
            >
              💼 Back to Jobs
            </button>
          )}
        </div>
      </header>

      {/* Warnings */}
      {health && health.warnings.length > 0 && (
        <div style={{ padding: '0.75rem 2rem', background: 'rgba(245, 158, 11, 0.05)', borderBottom: '1px solid rgba(245, 158, 11, 0.15)' }}>
          {health.warnings.map((w, i) => (
            <p key={i} style={{ fontSize: '0.75rem', color: '#f59e0b' }}>⚠ {w}</p>
          ))}
        </div>
      )}

      {/* Agent Cards Grid */}
      <div className="ag-grid">
        {/* JobScan Agent */}
        <AgentCard
          title="JobScan Agent"
          description="Scan 45+ career portals via Greenhouse, Ashby & Lever APIs. Zero LLM tokens — pure HTTP + JSON."
          icon="🔍"
          accentColor="#06b6d4"
          defaultExpanded={true}
        >
          <ScanPanel />
        </AgentCard>

        {/* Scoring Agent */}
        <AgentCard
          title="Scoring Agent"
          description="Evaluate job-candidate fit using A-F scoring across 10 dimensions. Groq for speed, Gemini for depth."
          icon="📊"
          accentColor="#10b981"
        >
          <ScorePanel />
        </AgentCard>

        {/* CV Tailor Agent */}
        <AgentCard
          title="CV Tailor Agent"
          description="Generate ATS-optimized, JD-tailored CVs with keyword injection and compliance scoring."
          icon="✂️"
          accentColor="#d946ef"
        >
          <TailorPanel />
        </AgentCard>

        {/* Batch Agent */}
        <AgentCard
          title="Batch Agent"
          description="Process 100+ job URLs in parallel with semaphore-controlled concurrency and crash recovery."
          icon="⚡"
          accentColor="#f59e0b"
        >
          <BatchPanel />
        </AgentCard>

        {/* Tracker Agent */}
        <AgentCard
          title="Tracker Agent"
          description="Pipeline status tracking with conversion analytics, status management, and reporting."
          icon="📋"
          accentColor="#3b82f6"
          defaultExpanded={true}
        >
          <TrackerPanel />
        </AgentCard>
      </div>
    </div>
  );
}
