import { useState } from 'react';
import { runBatch, fetchBatchStatus } from '../../api/agentApi';
import type { BatchResponse, BatchStatusResponse, AgentStatus } from '../../types/agentTypes';

export default function BatchPanel() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [urlsText, setUrlsText] = useState('');
  const [cvText, setCvText] = useState('');
  const [concurrency, setConcurrency] = useState(5);
  const [result, setResult] = useState<BatchResponse | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);
  const [error, setError] = useState('');

  const handleBatch = async () => {
    const urls = urlsText.split('\n').map(l => l.trim()).filter(l => l.startsWith('http'));
    if (urls.length === 0) { setError('No valid URLs found'); return; }

    setStatus('running');
    setError('');
    setResult(null);
    try {
      const data = await runBatch({
        urls,
        cv_text: cvText.trim() || undefined,
        concurrency,
      });
      if (data.status === 'error') {
        setError(data.error || 'Batch processing failed');
        setStatus('error');
      } else {
        setResult(data);
        setStatus('complete');
      }
    } catch (err: any) {
      setError(err.message || 'Batch request failed');
      setStatus('error');
    }
  };

  const handleCheckStatus = async () => {
    try {
      const data = await fetchBatchStatus();
      setBatchStatus(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const pct = result && result.total > 0 ? ((result.completed / result.total) * 100) : 0;

  return (
    <div>
      {/* URL Input */}
      <textarea
        className="ag-input ag-textarea"
        placeholder="Paste URLs (one per line)..."
        value={urlsText}
        onChange={(e) => setUrlsText(e.target.value)}
        style={{ minHeight: '70px' }}
      />

      <textarea
        className="ag-input ag-textarea"
        placeholder="CV text (optional — uses default cv.md)..."
        value={cvText}
        onChange={(e) => setCvText(e.target.value)}
        style={{ marginTop: '0.375rem', minHeight: '40px' }}
      />

      {/* Concurrency Slider */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--ag-text-muted)' }}>
        <span>Workers:</span>
        <input
          type="range" min="1" max="10" value={concurrency}
          onChange={(e) => setConcurrency(parseInt(e.target.value))}
          style={{ flex: 1, accentColor: 'var(--ag-accent)' }}
        />
        <span style={{ color: 'var(--ag-text)', fontWeight: 600 }}>{concurrency}</span>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
        <button className="ag-btn ag-btn-ghost ag-btn-sm" onClick={handleCheckStatus}>📋 Check Status</button>
        <button className="ag-btn ag-btn-primary ag-btn-sm" onClick={handleBatch} disabled={status === 'running'}>
          {status === 'running' ? <><span className="ag-spinner" /> Processing...</> : '⚡ Run Batch'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="ag-result" style={{ borderColor: 'var(--ag-error)' }}>
          <p style={{ color: 'var(--ag-error)', fontSize: '0.8125rem' }}>⚠ {error}</p>
        </div>
      )}

      {/* Batch Status Quick View */}
      {batchStatus && batchStatus.status === 'ok' && (
        <div className="ag-result">
          <p className="ag-result-title">Batch Status</p>
          <div className="ag-stats">
            <div className="ag-stat"><span className="ag-stat-value">{batchStatus.total}</span><span className="ag-stat-label">Total</span></div>
            <div className="ag-stat"><span className="ag-stat-value">{batchStatus.pending}</span><span className="ag-stat-label">Pending</span></div>
            <div className="ag-stat"><span className="ag-stat-value" style={{ color: 'var(--ag-success)' }}>{batchStatus.completed}</span><span className="ag-stat-label">Done</span></div>
            <div className="ag-stat"><span className="ag-stat-value" style={{ color: 'var(--ag-error)' }}>{batchStatus.failed}</span><span className="ag-stat-label">Failed</span></div>
          </div>
        </div>
      )}

      {/* Batch Result */}
      {result && result.status === 'ok' && (
        <div className="ag-result">
          {/* Progress Bar */}
          <div className="ag-progress">
            <div className="ag-progress-fill" style={{ width: `${pct}%` }} />
          </div>

          <div className="ag-stats">
            <div className="ag-stat"><span className="ag-stat-value">{result.total}</span><span className="ag-stat-label">Total</span></div>
            <div className="ag-stat"><span className="ag-stat-value" style={{ color: 'var(--ag-success)' }}>{result.completed}</span><span className="ag-stat-label">Done</span></div>
            <div className="ag-stat"><span className="ag-stat-value" style={{ color: 'var(--ag-error)' }}>{result.failed}</span><span className="ag-stat-label">Failed</span></div>
            <div className="ag-stat"><span className="ag-stat-value">{result.elapsed_seconds}s</span><span className="ag-stat-label">Time</span></div>
          </div>

          {/* Results Table */}
          {result.results.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <p className="ag-result-title">Job Results</p>
              <div className="ag-scroll" style={{ maxHeight: '150px' }}>
                {result.results.map((job, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0.375rem 0', borderBottom: '1px solid rgba(42,42,58,0.4)', fontSize: '0.75rem',
                  }}>
                    <span style={{ color: 'var(--ag-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60%' }}>
                      {job.url}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {job.score != null && (
                        <span style={{ fontWeight: 600, color: job.score >= 4 ? 'var(--ag-success)' : 'var(--ag-warning)' }}>
                          {job.score.toFixed(1)}
                        </span>
                      )}
                      <span className={`ag-tag ag-tag-${job.status === 'completed' ? 'offer' : job.status === 'failed' ? 'rejected' : 'evaluated'}`}>
                        {job.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
