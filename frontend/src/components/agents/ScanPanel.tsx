import { useState } from 'react';
import { runScan } from '../../api/agentApi';
import type { ScanResponse, AgentStatus } from '../../types/agentTypes';

export default function ScanPanel() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [company, setCompany] = useState('');
  const [dryRun, setDryRun] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState('');

  const handleScan = async () => {
    setStatus('running');
    setError('');
    setResult(null);
    try {
      const data = await runScan(company || undefined, dryRun);
      if (data.status === 'error') {
        setError((data as any).error || 'Scan failed');
        setStatus('error');
      } else {
        setResult(data);
        setStatus('complete');
      }
    } catch (err: any) {
      setError(err.message || 'Scan request failed');
      setStatus('error');
    }
  };

  return (
    <div>
      {/* Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <input
          className="ag-input"
          type="text"
          placeholder="Company filter (optional)..."
          value={company}
          onChange={(e) => setCompany(e.target.value)}
        />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <label className="ag-toggle">
            <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
            Dry Run
          </label>
          <button
            className="ag-btn ag-btn-primary ag-btn-sm"
            onClick={handleScan}
            disabled={status === 'running'}
          >
            {status === 'running' ? <><span className="ag-spinner" /> Scanning...</> : '🔍 Scan Portals'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="ag-result" style={{ borderColor: 'var(--ag-error)' }}>
          <p style={{ color: 'var(--ag-error)', fontSize: '0.8125rem' }}>⚠ {error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="ag-result">
          <div className="ag-stats">
            <div className="ag-stat">
              <span className="ag-stat-value">{result.companies_scanned}</span>
              <span className="ag-stat-label">Scanned</span>
            </div>
            <div className="ag-stat">
              <span className="ag-stat-value">{result.total_found}</span>
              <span className="ag-stat-label">Found</span>
            </div>
            <div className="ag-stat">
              <span className="ag-stat-value" style={{ color: 'var(--ag-success)' }}>{result.new_offers.length}</span>
              <span className="ag-stat-label">New</span>
            </div>
            <div className="ag-stat">
              <span className="ag-stat-value">{result.duplicates}</span>
              <span className="ag-stat-label">Dupes</span>
            </div>
          </div>

          {result.new_offers.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <p className="ag-result-title">New Offers</p>
              <div className="ag-scroll" style={{ maxHeight: '160px' }}>
                {result.new_offers.map((offer, i) => (
                  <div key={i} className="ag-offer-row">
                    <span style={{ color: 'var(--ag-text)', fontWeight: 500 }}>{offer.company}</span>
                    <span style={{ color: 'var(--ag-accent-light)' }}>{offer.title}</span>
                    <span style={{ color: 'var(--ag-text-muted)' }}>{offer.location || '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.errors.length > 0 && (
            <div className="ag-log" style={{ marginTop: '0.5rem' }}>
              {result.errors.map((e, i) => (
                <div key={i} className="ag-log-entry ag-log-err">✗ {e.company}: {e.error}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
