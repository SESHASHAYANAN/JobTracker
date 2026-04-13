import { useState } from 'react';
import { runScore } from '../../api/agentApi';
import type { ScoreResponse, AgentStatus } from '../../types/agentTypes';

export default function ScorePanel() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [url, setUrl] = useState('');
  const [jdText, setJdText] = useState('');
  const [cvText, setCvText] = useState('');
  const [inputMode, setInputMode] = useState<'url' | 'text'>('url');
  const [result, setResult] = useState<ScoreResponse | null>(null);
  const [error, setError] = useState('');

  const handleScore = async () => {
    setStatus('running');
    setError('');
    setResult(null);
    try {
      const params: Record<string, string> = {};
      if (inputMode === 'url') params.url = url;
      else params.jd_text = jdText;
      if (cvText.trim()) params.cv_text = cvText;

      const data = await runScore(params);
      if (data.status === 'error') {
        setError(data.error || 'Scoring failed');
        setStatus('error');
      } else {
        setResult(data);
        setStatus('complete');
      }
    } catch (err: any) {
      setError(err.message || 'Score request failed');
      setStatus('error');
    }
  };

  const gradeColor = (g: string) => {
    const map: Record<string, string> = { A: '#10b981', B: '#34d399', C: '#f59e0b', D: '#f97316', E: '#ef4444', F: '#dc2626' };
    return map[g] || 'var(--ag-text)';
  };

  return (
    <div>
      {/* Mode Tabs */}
      <div className="ag-tabs">
        <button className={`ag-tab ${inputMode === 'url' ? 'ag-tab-active' : ''}`} onClick={() => setInputMode('url')}>URL</button>
        <button className={`ag-tab ${inputMode === 'text' ? 'ag-tab-active' : ''}`} onClick={() => setInputMode('text')}>Paste JD</button>
      </div>

      {/* Input */}
      {inputMode === 'url' ? (
        <input className="ag-input" type="text" placeholder="Job posting URL..." value={url} onChange={(e) => setUrl(e.target.value)} />
      ) : (
        <textarea className="ag-input ag-textarea" placeholder="Paste job description..." value={jdText} onChange={(e) => setJdText(e.target.value)} />
      )}

      <textarea
        className="ag-input ag-textarea"
        placeholder="CV text (optional — uses default cv.md if empty)..."
        value={cvText}
        onChange={(e) => setCvText(e.target.value)}
        style={{ marginTop: '0.5rem', minHeight: '50px' }}
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
        <button className="ag-btn ag-btn-primary ag-btn-sm" onClick={handleScore} disabled={status === 'running' || (!url && !jdText)}>
          {status === 'running' ? <><span className="ag-spinner" /> Scoring...</> : '📊 Evaluate'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="ag-result" style={{ borderColor: 'var(--ag-error)' }}>
          <p style={{ color: 'var(--ag-error)', fontSize: '0.8125rem' }}>⚠ {error}</p>
        </div>
      )}

      {/* Results */}
      {result && result.status === 'ok' && (
        <div className="ag-result">
          {/* Title + Grade */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <div>
              <p style={{ fontWeight: 600, color: 'var(--ag-text)' }}>{result.company}</p>
              <p style={{ fontSize: '0.75rem', color: 'var(--ag-accent-light)' }}>{result.role}</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span className="ag-grade" style={{ color: gradeColor(result.grade) }}>{result.grade}</span>
              <p style={{ fontSize: '0.6875rem', color: 'var(--ag-text-muted)' }}>{result.overall_score}/5.0</p>
            </div>
          </div>

          {/* Recommendation */}
          <p style={{
            fontSize: '0.8125rem',
            padding: '0.375rem 0.625rem',
            borderRadius: '0.375rem',
            background: result.overall_score >= 4.0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            color: result.overall_score >= 4.0 ? 'var(--ag-success)' : 'var(--ag-warning)',
            marginBottom: '0.75rem',
          }}>
            {result.recommendation}
          </p>

          {/* Dimensions */}
          <p className="ag-result-title">Dimensions</p>
          <div className="ag-scroll" style={{ maxHeight: '200px' }}>
            {result.dimensions.map((dim, i) => (
              <div key={i} className="ag-dim-row">
                <span className="ag-dim-label">{dim.name}</span>
                <div className="ag-dim-bar">
                  <div className="ag-dim-fill" style={{ width: `${(dim.score / 5) * 100}%` }} />
                </div>
                <span className="ag-dim-value">{dim.score.toFixed(1)}</span>
              </div>
            ))}
          </div>

          {/* Gaps */}
          {result.gaps.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <p className="ag-result-title">Gaps</p>
              {result.gaps.map((gap, i) => (
                <div key={i} style={{ fontSize: '0.75rem', color: 'var(--ag-warning)', padding: '0.125rem 0' }}>
                  ⚠ {gap}
                  {result.gap_mitigations[i] && (
                    <span style={{ color: 'var(--ag-text-muted)', marginLeft: '0.5rem' }}>→ {result.gap_mitigations[i]}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Keywords */}
          {result.keywords.length > 0 && (
            <div className="ag-keywords" style={{ marginTop: '0.5rem' }}>
              {result.keywords.slice(0, 12).map((kw, i) => (
                <span key={i} className="ag-keyword">{kw}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
