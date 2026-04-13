import { useState } from 'react';
import { runTailor } from '../../api/agentApi';
import type { TailorResponse, AgentStatus } from '../../types/agentTypes';

export default function TailorPanel() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [url, setUrl] = useState('');
  const [jdText, setJdText] = useState('');
  const [cvText, setCvText] = useState('');
  const [inputMode, setInputMode] = useState<'url' | 'text'>('url');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [result, setResult] = useState<TailorResponse | null>(null);
  const [error, setError] = useState('');

  const handleTailor = async () => {
    setStatus('running');
    setError('');
    setResult(null);
    try {
      const params: Record<string, string> = {};
      if (inputMode === 'url') params.url = url;
      else params.jd_text = jdText;
      if (cvText.trim()) params.cv_text = cvText;
      if (company.trim()) params.company = company;
      if (role.trim()) params.role = role;

      const data = await runTailor(params);
      if (data.status === 'error') {
        setError(data.error || 'Tailoring failed');
        setStatus('error');
      } else {
        setResult(data);
        setStatus('complete');
      }
    } catch (err: any) {
      setError(err.message || 'Tailor request failed');
      setStatus('error');
    }
  };

  const circumference = 2 * Math.PI * 34;
  const atsOffset = result ? circumference - (result.ats_score / 100) * circumference : circumference;
  const kwOffset = result ? circumference - (result.keyword_coverage / 100) * circumference : circumference;

  return (
    <div>
      {/* Mode Tabs */}
      <div className="ag-tabs">
        <button className={`ag-tab ${inputMode === 'url' ? 'ag-tab-active' : ''}`} onClick={() => setInputMode('url')}>URL</button>
        <button className={`ag-tab ${inputMode === 'text' ? 'ag-tab-active' : ''}`} onClick={() => setInputMode('text')}>Paste JD</button>
      </div>

      {/* Inputs */}
      {inputMode === 'url' ? (
        <input className="ag-input" type="text" placeholder="Job posting URL..." value={url} onChange={(e) => setUrl(e.target.value)} />
      ) : (
        <textarea className="ag-input ag-textarea" placeholder="Paste job description..." value={jdText} onChange={(e) => setJdText(e.target.value)} />
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.375rem', marginTop: '0.375rem' }}>
        <input className="ag-input" type="text" placeholder="Company..." value={company} onChange={(e) => setCompany(e.target.value)} />
        <input className="ag-input" type="text" placeholder="Role..." value={role} onChange={(e) => setRole(e.target.value)} />
      </div>

      <textarea
        className="ag-input ag-textarea"
        placeholder="CV text (optional — uses default cv.md)..."
        value={cvText}
        onChange={(e) => setCvText(e.target.value)}
        style={{ marginTop: '0.375rem', minHeight: '50px' }}
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
        <button className="ag-btn ag-btn-primary ag-btn-sm" onClick={handleTailor} disabled={status === 'running' || (!url && !jdText)}>
          {status === 'running' ? <><span className="ag-spinner" /> Tailoring...</> : '✂️ Tailor CV'}
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
          {/* Gauges */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginBottom: '0.75rem' }}>
            {/* ATS Score Gauge */}
            <div style={{ textAlign: 'center' }}>
              <div className="ag-gauge">
                <svg width="80" height="80" viewBox="0 0 80 80">
                  <circle className="ag-gauge-circle" cx="40" cy="40" r="34" />
                  <circle
                    className="ag-gauge-value"
                    cx="40" cy="40" r="34"
                    stroke="var(--ag-accent)"
                    strokeDasharray={circumference}
                    strokeDashoffset={atsOffset}
                  />
                </svg>
                <span className="ag-gauge-text">{result.ats_score}%</span>
              </div>
              <p style={{ fontSize: '0.625rem', color: 'var(--ag-text-muted)', marginTop: '0.25rem' }}>ATS Score</p>
            </div>

            {/* Keyword Coverage Gauge */}
            <div style={{ textAlign: 'center' }}>
              <div className="ag-gauge">
                <svg width="80" height="80" viewBox="0 0 80 80">
                  <circle className="ag-gauge-circle" cx="40" cy="40" r="34" />
                  <circle
                    className="ag-gauge-value"
                    cx="40" cy="40" r="34"
                    stroke="var(--ag-cyan)"
                    strokeDasharray={circumference}
                    strokeDashoffset={kwOffset}
                  />
                </svg>
                <span className="ag-gauge-text">{result.keyword_coverage}%</span>
              </div>
              <p style={{ fontSize: '0.625rem', color: 'var(--ag-text-muted)', marginTop: '0.25rem' }}>Keywords</p>
            </div>
          </div>

          {/* Injected Keywords */}
          {result.keywords_injected.length > 0 && (
            <div>
              <p className="ag-result-title">Injected Keywords</p>
              <div className="ag-keywords">
                {result.keywords_injected.map((kw, i) => (
                  <span key={i} className="ag-keyword">{kw}</span>
                ))}
              </div>
            </div>
          )}

          {/* Sections */}
          {result.sections.length > 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <p className="ag-result-title">Tailored Sections</p>
              <div className="ag-scroll" style={{ maxHeight: '180px' }}>
                {result.sections.map((sec, i) => (
                  <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid rgba(42,42,58,0.4)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--ag-text)' }}>{sec.name}</span>
                      <span style={{ fontSize: '0.625rem', color: 'var(--ag-cyan)' }}>{sec.keywords_used.length} keywords</span>
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--ag-text-muted)', marginTop: '0.25rem', lineHeight: 1.5 }}>
                      {sec.tailored.substring(0, 200)}{sec.tailored.length > 200 ? '...' : ''}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Output paths */}
          <div style={{ marginTop: '0.5rem', fontSize: '0.6875rem', color: 'var(--ag-text-muted)' }}>
            {result.pdf_path && <p>📄 PDF: {result.pdf_path}</p>}
            {result.html_path && <p>🌐 HTML: {result.html_path}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
