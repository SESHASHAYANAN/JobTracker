import { useState, useEffect } from 'react';
import { fetchTracker, fetchAnalytics, updateTrackerStatus } from '../../api/agentApi';
import type { TrackerResponse, PipelineAnalytics, PipelineEntry, AgentStatus, JobStatus } from '../../types/agentTypes';

const STATUSES: JobStatus[] = ['Evaluated', 'Applied', 'Responded', 'Interview', 'Offer', 'Rejected', 'Discarded', 'SKIP'];

const statusTagClass = (s: string) => {
  const map: Record<string, string> = {
    Evaluated: 'ag-tag-evaluated',
    Applied: 'ag-tag-applied',
    Responded: 'ag-tag-responded',
    Interview: 'ag-tag-interview',
    Offer: 'ag-tag-offer',
    Rejected: 'ag-tag-rejected',
    Discarded: 'ag-tag-discarded',
    SKIP: 'ag-tag-discarded',
  };
  return map[s] || '';
};

export default function TrackerPanel() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [data, setData] = useState<TrackerResponse | null>(null);
  const [analytics, setAnalytics] = useState<PipelineAnalytics | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [error, setError] = useState('');

  const loadTracker = async () => {
    setStatus('running');
    setError('');
    try {
      const res = await fetchTracker(filterStatus || undefined);
      if (res.status === 'ok') {
        setData(res);
        setStatus('complete');
      } else {
        setError('Failed to load tracker');
        setStatus('error');
      }
    } catch (err: any) {
      setError(err.message);
      setStatus('error');
    }
  };

  const loadAnalytics = async () => {
    try {
      const res = await fetchAnalytics();
      if (res.status === 'ok') {
        setAnalytics(res.analytics);
        setShowAnalytics(true);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleStatusUpdate = async (entry: PipelineEntry, newStatus: string) => {
    try {
      await updateTrackerStatus(entry.company, entry.role, newStatus);
      loadTracker();  // refresh
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadTracker();
  }, [filterStatus]);

  return (
    <div>
      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', gap: '0.25rem', overflowX: 'auto' }}>
          <button className={`ag-tab ${filterStatus === '' ? 'ag-tab-active' : ''}`} onClick={() => setFilterStatus('')}>All</button>
          {STATUSES.map(s => (
            <button key={s} className={`ag-tab ${filterStatus === s ? 'ag-tab-active' : ''}`} onClick={() => setFilterStatus(s)}>
              {s}
            </button>
          ))}
        </div>
        <button className="ag-btn ag-btn-secondary ag-btn-sm" onClick={loadAnalytics}>📈 Analytics</button>
      </div>

      {/* Error */}
      {error && (
        <div className="ag-result" style={{ borderColor: 'var(--ag-error)' }}>
          <p style={{ color: 'var(--ag-error)', fontSize: '0.8125rem' }}>⚠ {error}</p>
        </div>
      )}

      {/* Summary Stats */}
      {data && data.summary && (
        <div className="ag-stats" style={{ marginBottom: '0.75rem' }}>
          <div className="ag-stat"><span className="ag-stat-value">{data.summary.total_entries}</span><span className="ag-stat-label">Total</span></div>
          <div className="ag-stat"><span className="ag-stat-value">{data.summary.avg_score.toFixed(1)}</span><span className="ag-stat-label">Avg Score</span></div>
          {Object.entries(data.summary.by_status).slice(0, 4).map(([k, v]) => (
            <div key={k} className="ag-stat"><span className="ag-stat-value">{v}</span><span className="ag-stat-label">{k}</span></div>
          ))}
        </div>
      )}

      {/* Entries Table */}
      {data && data.entries.length > 0 ? (
        <div className="ag-scroll" style={{ maxHeight: '280px' }}>
          {/* Header */}
          <div className="ag-pipeline-row" style={{ fontWeight: 600, fontSize: '0.6875rem', color: 'var(--ag-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <span>#</span>
            <span>Date</span>
            <span>Company</span>
            <span>Role</span>
            <span>Score</span>
            <span>Status</span>
            <span>PDF</span>
          </div>
          {data.entries.map((entry, i) => (
            <div key={i} className="ag-pipeline-row">
              <span style={{ color: 'var(--ag-text-muted)', fontSize: '0.75rem' }}>{entry.number}</span>
              <span style={{ color: 'var(--ag-text-muted)', fontSize: '0.75rem' }}>{entry.date}</span>
              <span style={{ color: 'var(--ag-text)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{entry.company}</span>
              <span style={{ color: 'var(--ag-accent-light)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{entry.role}</span>
              <span style={{ fontWeight: 600, color: entry.score && entry.score >= 4 ? 'var(--ag-success)' : 'var(--ag-text)' }}>
                {entry.score ? entry.score.toFixed(1) : '—'}
              </span>
              <select
                value={entry.status}
                onChange={(e) => handleStatusUpdate(entry, e.target.value)}
                onClick={(e) => e.stopPropagation()}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'inherit',
                  fontSize: '0.6875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: '0.125rem',
                }}
                className={`ag-tag ${statusTagClass(entry.status)}`}
              >
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <span style={{ textAlign: 'center' }}>{entry.pdf_generated ? '✅' : '❌'}</span>
            </div>
          ))}
        </div>
      ) : status !== 'running' ? (
        <div className="ag-empty">
          <span className="ag-empty-icon">📋</span>
          <p style={{ fontSize: '0.8125rem' }}>No tracked applications yet</p>
          <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>Score some jobs to populate the tracker.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem' }}>
          <span className="ag-spinner" />
        </div>
      )}

      {/* Analytics Panel */}
      {showAnalytics && analytics && (
        <div className="ag-result" style={{ marginTop: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <p className="ag-result-title" style={{ margin: 0 }}>Pipeline Analytics</p>
            <button className="ag-btn ag-btn-ghost ag-btn-sm" onClick={() => setShowAnalytics(false)}>✕</button>
          </div>

          {/* Conversion Rates */}
          {Object.keys(analytics.conversion_rates).length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <p style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--ag-text-muted)', marginBottom: '0.375rem' }}>Conversion Rates</p>
              {Object.entries(analytics.conversion_rates).map(([stage, rate]) => (
                <div key={stage} className="ag-dim-row">
                  <span className="ag-dim-label">{stage}</span>
                  <div className="ag-dim-bar">
                    <div className="ag-dim-fill" style={{ width: `${rate}%` }} />
                  </div>
                  <span className="ag-dim-value">{rate}%</span>
                </div>
              ))}
            </div>
          )}

          {/* Insights */}
          {analytics.insights.length > 0 && (
            <div>
              <p style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--ag-text-muted)', marginBottom: '0.375rem' }}>Insights</p>
              {analytics.insights.map((insight, i) => (
                <p key={i} style={{ fontSize: '0.75rem', color: 'var(--ag-text)', padding: '0.125rem 0' }}>💡 {insight}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
