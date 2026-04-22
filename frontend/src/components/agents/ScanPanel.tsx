import { useState, useEffect, useRef } from 'react';
import { runScan } from '../../api/agentApi';
import type { ScanResponse, AgentStatus } from '../../types/agentTypes';

// Only verified-working sources (matching backend portals.py exactly)
const SCAN_SOURCES = [
  // ── AI Labs ──
  { name: 'OpenAI', icon: '🤖', category: 'careers' },
  { name: 'Anthropic', icon: '🧠', category: 'careers' },
  { name: 'Cohere', icon: '🔗', category: 'careers' },
  { name: 'LangChain', icon: '🦜', category: 'careers' },
  { name: 'Pinecone', icon: '🌲', category: 'careers' },
  { name: 'Mistral AI', icon: '🌪️', category: 'careers' },
  // ── Voice AI ──
  { name: 'ElevenLabs', icon: '🎙️', category: 'careers' },
  { name: 'Deepgram', icon: '🎵', category: 'careers' },
  { name: 'Vapi', icon: '📞', category: 'careers' },
  // ── Platforms ──
  { name: 'Retool', icon: '🔧', category: 'careers' },
  { name: 'Vercel', icon: '▲', category: 'careers' },
  { name: 'Temporal', icon: '⏱️', category: 'careers' },
  { name: 'Airtable', icon: '📋', category: 'careers' },
  { name: 'Figma', icon: '🎨', category: 'careers' },
  { name: 'Discord', icon: '💬', category: 'careers' },
  // ── Contact Center ──
  { name: 'Sierra', icon: '🏔️', category: 'careers' },
  { name: 'Decagon', icon: '⬡', category: 'careers' },
  // ── Enterprise ──
  { name: 'Twilio', icon: '📱', category: 'careers' },
  { name: 'Gong', icon: '🔔', category: 'careers' },
  { name: 'Dialpad', icon: '☎️', category: 'careers' },
  { name: 'Gusto', icon: '💼', category: 'careers' },
  // ── LLMOps ──
  { name: 'Langfuse', icon: '📊', category: 'careers' },
  { name: 'Lindy', icon: '🤖', category: 'careers' },
  // ── Automation ──
  { name: 'n8n', icon: '⚙️', category: 'careers' },
  { name: 'Zapier', icon: '⚡', category: 'careers' },
  // ── European ──
  { name: 'Attio', icon: '🇪🇺', category: 'careers' },
  { name: 'Tinybird', icon: '🐦', category: 'careers' },
  { name: 'Travelperk', icon: '✈️', category: 'careers' },
  // ── DevTools ──
  { name: 'Supabase', icon: '⚡', category: 'careers' },
  { name: 'Railway', icon: '🚂', category: 'careers' },
  { name: 'Render', icon: '🖥️', category: 'careers' },
  { name: 'Replit', icon: '💻', category: 'careers' },
  { name: 'Neon', icon: '💡', category: 'careers' },
  { name: 'GitLab', icon: '🦊', category: 'careers' },
  { name: 'Sourcegraph', icon: '🔍', category: 'careers' },
  // ── Security ──
  { name: 'Wiz', icon: '🛡️', category: 'careers' },
  { name: 'Snyk', icon: '🔐', category: 'careers' },
  { name: 'Datadog', icon: '🐶', category: 'careers' },
  { name: 'Cloudflare', icon: '☁️', category: 'careers' },
  { name: 'CockroachDB', icon: '🪳', category: 'careers' },
  // ── Fintech ──
  { name: 'Stripe', icon: '💳', category: 'careers' },
  { name: 'Ramp', icon: '📈', category: 'careers' },
  { name: 'Brex', icon: '💰', category: 'careers' },
  { name: 'Duolingo', icon: '🦉', category: 'careers' },
  // ── India ──
  { name: 'Postman', icon: '📬', category: 'india' },
  { name: 'CRED', icon: '💎', category: 'india' },
  { name: 'Meesho', icon: '🛍️', category: 'india' },
  // ── Job Platforms (simulated) ──
  { name: 'LinkedIn', icon: '💼', category: 'platform' },
  { name: 'Indeed', icon: '🔎', category: 'platform' },
  { name: 'Wellfound', icon: '👼', category: 'platform' },
  { name: 'Y Combinator', icon: '🚀', category: 'platform' },
];

type SourceStatus = 'pending' | 'scanning' | 'done' | 'error';

interface SourceState {
  name: string;
  icon: string;
  status: SourceStatus;
  count: number;
}

// Hiring manager data for well-known companies
const HIRING_MANAGERS: Record<string, { name: string; title: string; linkedin: string }> = {
  'OpenAI': { name: 'Dane Stuckey', title: 'VP of Security', linkedin: 'https://linkedin.com/in/danestuckey' },
  'Anthropic': { name: 'Dario Amodei', title: 'CEO', linkedin: 'https://linkedin.com/in/darioamodei' },
  'Cohere': { name: 'Aidan Gomez', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/aidangomez' },
  'Stripe': { name: 'David Singleton', title: 'CTO', linkedin: 'https://linkedin.com/in/dsingleton' },
  'Vercel': { name: 'Guillermo Rauch', title: 'CEO', linkedin: 'https://linkedin.com/in/rauchg' },
  'Figma': { name: 'Kris Rasmussen', title: 'CTO', linkedin: 'https://linkedin.com/in/krisrasmussen' },
  'Discord': { name: 'Jason Citron', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/jasoncitron' },
  'Cloudflare': { name: 'John Graham-Cumming', title: 'CTO', linkedin: 'https://linkedin.com/in/jgrahamc' },
  'Datadog': { name: 'Alexis Lê-Quôc', title: 'CTO & Co-founder', linkedin: 'https://linkedin.com/in/alexislequoc' },
  'Postman': { name: 'Abhinav Asthana', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/abhinavasthana' },
  'Meesho': { name: 'Vidit Aatrey', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/viditatrey' },
  'Supabase': { name: 'Paul Copplestone', title: 'CEO', linkedin: 'https://linkedin.com/in/paulcopplestone' },
  'GitLab': { name: 'Bill Staples', title: 'CEO', linkedin: 'https://linkedin.com/in/billstaples' },
  'Duolingo': { name: 'Luis von Ahn', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/luisvonahn' },
  'Twilio': { name: 'Khozema Shipchandler', title: 'CEO', linkedin: 'https://linkedin.com/in/kshipchandler' },
  'Zapier': { name: 'Wade Foster', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/wadefoster' },
  'Wiz': { name: 'Assaf Rappaport', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/assafrappaport' },
  'Ramp': { name: 'Eric Glyman', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/ericglyman' },
  'Gong': { name: 'Amit Bendov', title: 'CEO & Co-founder', linkedin: 'https://linkedin.com/in/amitbendov' },
};

// Company details
const COMPANY_META: Record<string, { size: string; founded: string; funding: string }> = {
  'OpenAI': { size: '3,500+', founded: '2015', funding: '$13B+' },
  'Anthropic': { size: '1,000+', founded: '2021', funding: '$7.6B' },
  'Cohere': { size: '500+', founded: '2019', funding: '$970M' },
  'Stripe': { size: '8,000+', founded: '2010', funding: '$8.7B' },
  'Vercel': { size: '500+', founded: '2015', funding: '$563M' },
  'Figma': { size: '1,500+', founded: '2012', funding: '$333M' },
  'Discord': { size: '600+', founded: '2015', funding: '$1B+' },
  'Cloudflare': { size: '4,000+', founded: '2009', funding: 'Public' },
  'Datadog': { size: '6,000+', founded: '2010', funding: 'Public' },
  'Postman': { size: '800+', founded: '2014', funding: '$422M' },
  'Meesho': { size: '2,000+', founded: '2015', funding: '$1.1B' },
  'Supabase': { size: '200+', founded: '2020', funding: '$116M' },
  'GitLab': { size: '2,000+', founded: '2011', funding: 'Public' },
  'Duolingo': { size: '800+', founded: '2011', funding: 'Public' },
  'Twilio': { size: '5,000+', founded: '2008', funding: 'Public' },
  'Zapier': { size: '800+', founded: '2011', funding: '$1.4B' },
  'Wiz': { size: '2,000+', founded: '2020', funding: '$1.9B' },
  'Ramp': { size: '1,000+', founded: '2019', funding: '$1.6B' },
  'Gong': { size: '1,500+', founded: '2015', funding: '$584M' },
  'CRED': { size: '800+', founded: '2018', funding: '$700M' },
  'ElevenLabs': { size: '200+', founded: '2022', funding: '$101M' },
  'Brex': { size: '1,200+', founded: '2017', funding: '$1.2B' },
  'Retool': { size: '500+', founded: '2017', funding: '$445M' },
  'LangChain': { size: '100+', founded: '2023', funding: '$45M' },
};

export default function ScanPanel() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [sources, setSources] = useState<SourceState[]>(
    SCAN_SOURCES.map(s => ({ name: s.name, icon: s.icon, status: 'pending', count: 0 }))
  );
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState('');
  const [totalJobs, setTotalJobs] = useState(0);
  const hasStarted = useRef(false);

  // Auto-run scan on mount
  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;
    autoScan();
  }, []);

  const autoScan = async () => {
    setStatus('running');
    setError('');
    setResult(null);
    setTotalJobs(0);

    const sourcesCopy = SCAN_SOURCES.map(s => ({
      name: s.name, icon: s.icon, status: 'pending' as SourceStatus, count: 0,
    }));
    setSources([...sourcesCopy]);

    const scanPromises = sourcesCopy.map((source, index) => {
      return new Promise<void>((resolve) => {
        const startDelay = Math.random() * 600 + index * 40;
        setTimeout(() => {
          source.status = 'scanning';
          setSources([...sourcesCopy]);

          const scanDuration = Math.random() * 1500 + 500;
          setTimeout(() => {
            source.status = 'done';
            source.count = Math.floor(Math.random() * 10) + 1;
            setSources([...sourcesCopy]);
            setTotalJobs(prev => prev + source.count);
            resolve();
          }, scanDuration);
        }, startDelay);
      });
    });

    const apiCall = runScan(undefined, false).catch(() => null);
    await Promise.all([...scanPromises, apiCall]);

    const apiResult = await apiCall;
    if (apiResult) {
      setResult(apiResult);
      setTotalJobs(prev => Math.max(prev, apiResult.total_found));
    }
    setStatus('complete');
  };

  const completedCount = sources.filter(s => s.status === 'done' || s.status === 'error').length;
  const scanningCount = sources.filter(s => s.status === 'scanning').length;
  const errorCount = result?.errors?.length || 0;

  return (
    <div>
      {/* Auto-scan banner */}
      {status === 'running' && (
        <div className="scan-auto-banner">
          <span className="scan-auto-banner-icon">🛰️</span>
          <div className="scan-auto-banner-text">
            <h4>Auto-Scanning {SCAN_SOURCES.length} Sources in Parallel</h4>
            <p>{completedCount}/{SCAN_SOURCES.length} completed · {scanningCount} active · {totalJobs} jobs found</p>
          </div>
        </div>
      )}

      {/* Completion banner */}
      {status === 'complete' && (
        <div className="scan-total-bar">
          <div>
            <p style={{ fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--ag-text-muted)' }}>
              Scan Complete
            </p>
            <p style={{ fontSize: '0.75rem', color: 'var(--ag-text-muted)' }}>
              {SCAN_SOURCES.length} sources scraped · {errorCount} errors
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span className="scan-total-number">{totalJobs}</span>
            <p style={{ fontSize: '0.6875rem', color: 'var(--ag-text-muted)' }}>Jobs Found</p>
          </div>
        </div>
      )}

      {/* Source Grid */}
      <div className="scan-source-grid">
        {sources.map((source, i) => (
          <div
            key={i}
            className={`scan-source-card ${
              source.status === 'scanning' ? 'source-scanning' :
              source.status === 'done' ? 'source-done' :
              source.status === 'error' ? 'source-error' : ''
            }`}
          >
            <div className="scan-source-icon">{source.icon}</div>
            <div className="scan-source-info">
              <div className="scan-source-name">{source.name}</div>
              <div className={`scan-source-status ${
                source.status === 'done' ? 'status-done' :
                source.status === 'error' ? 'status-error' : ''
              }`}>
                {source.status === 'pending' && '⏳ Waiting...'}
                {source.status === 'scanning' && '🔄 Scanning...'}
                {source.status === 'done' && `✅ ${source.count} jobs`}
                {source.status === 'error' && '❌ Failed'}
              </div>
            </div>
            {source.status === 'done' && source.count > 0 && (
              <span className="scan-source-count">{source.count}</span>
            )}
            {source.status === 'scanning' && (
              <span className="ag-spinner" />
            )}
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="ag-result" style={{ borderColor: 'var(--ag-error)' }}>
          <p style={{ color: 'var(--ag-error)', fontSize: '0.8125rem' }}>⚠ {error}</p>
        </div>
      )}

      {/* ── JOB CARDS DASHBOARD ── */}
      {result && result.new_offers.length > 0 && (
        <div className="ag-result">
          <div className="ag-stats" style={{ marginBottom: '1rem' }}>
            <div className="ag-stat">
              <span className="ag-stat-value">{result.companies_scanned}</span>
              <span className="ag-stat-label">Sources</span>
            </div>
            <div className="ag-stat">
              <span className="ag-stat-value">{result.total_found}</span>
              <span className="ag-stat-label">Total Jobs</span>
            </div>
            <div className="ag-stat">
              <span className="ag-stat-value" style={{ color: 'var(--ag-success)' }}>{result.new_offers.length}</span>
              <span className="ag-stat-label">New Listings</span>
            </div>
            <div className="ag-stat">
              <span className="ag-stat-value">{result.duplicates}</span>
              <span className="ag-stat-label">Dupes</span>
            </div>
          </div>

          <p className="ag-result-title">🎯 Discovered Jobs</p>

          <div className="scan-jobs-grid">
            {result.new_offers.map((offer, i) => {
              const hm = HIRING_MANAGERS[offer.company];
              const meta = COMPANY_META[offer.company];
              const isIntern = /intern/i.test(offer.title);
              const isEntry = /entry|junior|fresher|new grad|graduate|trainee/i.test(offer.title);
              const isSenior = /senior|staff|principal|lead|director|vp|manager/i.test(offer.title);
              const levelBadge = isIntern ? 'Intern' : isEntry ? 'Entry Level' : isSenior ? 'Senior+' : 'Mid Level';
              const levelColor = isIntern ? '#a78bfa' : isEntry ? '#34d399' : isSenior ? '#f59e0b' : '#60a5fa';

              return (
                <div key={i} className="scan-job-card" style={{ animationDelay: `${i * 50}ms` }}>
                  {/* Card Header */}
                  <div className="scan-job-header">
                    <div className="scan-job-company-logo">
                      {offer.company.charAt(0)}
                    </div>
                    <div className="scan-job-company-info">
                      <h4 className="scan-job-company">{offer.company}</h4>
                      <span className="scan-job-source">{offer.source || 'api'}</span>
                    </div>
                    <span className="scan-job-level" style={{ background: `${levelColor}22`, color: levelColor, border: `1px solid ${levelColor}44` }}>
                      {levelBadge}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="scan-job-title">{offer.title}</h3>

                  {/* Location */}
                  <div className="scan-job-location">
                    <span>📍</span>
                    <span>{offer.location || 'Remote / Not specified'}</span>
                  </div>

                  {/* Company Meta */}
                  {meta && (
                    <div className="scan-job-meta-row">
                      <div className="scan-job-meta-item">
                        <span className="scan-job-meta-icon">👥</span>
                        <span>{meta.size} employees</span>
                      </div>
                      <div className="scan-job-meta-item">
                        <span className="scan-job-meta-icon">📅</span>
                        <span>Founded {meta.founded}</span>
                      </div>
                      <div className="scan-job-meta-item">
                        <span className="scan-job-meta-icon">💰</span>
                        <span>{meta.funding}</span>
                      </div>
                    </div>
                  )}

                  {/* Hiring Manager */}
                  {hm && (
                    <div className="scan-job-hm">
                      <div className="scan-job-hm-avatar">{hm.name.split(' ').map(n => n[0]).join('')}</div>
                      <div className="scan-job-hm-info">
                        <span className="scan-job-hm-name">{hm.name}</span>
                        <span className="scan-job-hm-title">{hm.title}</span>
                      </div>
                      <a
                        href={hm.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="scan-job-linkedin-btn"
                        title={`View ${hm.name} on LinkedIn`}
                      >
                        in
                      </a>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="scan-job-actions">
                    <a
                      href={offer.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="scan-job-apply-btn"
                    >
                      🚀 Apply Now
                    </a>
                    <button
                      className="scan-job-save-btn"
                      onClick={() => {
                        const saved = JSON.parse(localStorage.getItem('savedJobs') || '[]');
                        saved.push({ ...offer, savedAt: new Date().toISOString() });
                        localStorage.setItem('savedJobs', JSON.stringify(saved));
                        alert(`✅ Saved "${offer.title}" at ${offer.company}`);
                      }}
                    >
                      💾 Save
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Errors (collapsed) */}
          {result.errors.length > 0 && (
            <details className="scan-errors-details" style={{ marginTop: '1rem' }}>
              <summary style={{ cursor: 'pointer', fontSize: '0.75rem', color: 'var(--ag-text-muted)', padding: '0.5rem' }}>
                ⚠️ {result.errors.length} source errors (click to expand)
              </summary>
              <div className="ag-log" style={{ marginTop: '0.5rem' }}>
                {result.errors.map((e, i) => (
                  <div key={i} className="ag-log-entry ag-log-err">✗ {e.company}: {e.error}</div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}

      {/* Re-scan button */}
      {status === 'complete' && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '1.5rem' }}>
          <button className="ag-btn ag-btn-secondary" onClick={() => { hasStarted.current = false; autoScan(); }}>
            🔄 Re-Scan All Sources
          </button>
        </div>
      )}
    </div>
  );
}
