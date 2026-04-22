/**
 * LiveApplyPopup — AI Apply rebuilt from scratch.
 *
 * No mocks. No placeholders. Real-time only.
 *
 * - Left panel: Profile form + controls
 * - Center panel: Live WebView (iframe) of the company's actual job page
 * - Right panel: Real activity log showing URL verification, page load, etc.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { applyToJob, rewriteResume } from '../api';
import WebViewFrame from './WebViewFrame';
import type { Job } from '../types';

interface LiveApplyPopupProps {
  job: Job;
  open: boolean;
  onClose: () => void;
}

type ApplyStatus = 'idle' | 'verifying' | 'loading' | 'live' | 'completed' | 'failed';

interface ActivityEntry {
  id: number;
  icon: string;
  label: string;
  detail: string;
  status: 'pending' | 'running' | 'done' | 'error' | 'skipped';
  timestamp: string;
}

export default function LiveApplyPopup({ job, open, onClose }: LiveApplyPopupProps) {
  // Profile form
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [linkedin, setLinkedin] = useState('');
  const [github, setGithub] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  // Advanced ATS rewrite
  const [advanced, setAdvanced] = useState(false);
  const [rewriteResult, setRewriteResult] = useState<any>(null);
  const [rewriting, setRewriting] = useState(false);
  const [showEditor, setShowEditor] = useState(false);

  // Apply state
  const [status, setStatus] = useState<ApplyStatus>('idle');
  const [applyUrl, setApplyUrl] = useState('');
  const [pageTitle, setPageTitle] = useState('');
  const [webViewState, setWebViewState] = useState<'loading' | 'loaded' | 'proxy' | 'failed'>('loading');
  const [elapsedMs, setElapsedMs] = useState(0);
  const [urlSource, setUrlSource] = useState('');
  const [liveVerified, setLiveVerified] = useState(false);

  // Activity log
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const activityIdRef = useRef(0);
  const stepsEndRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-scroll activity log
  useEffect(() => {
    stepsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activities]);

  // Timer
  useEffect(() => {
    if (status === 'verifying' || status === 'loading') {
      const start = Date.now() - elapsedMs;
      timerRef.current = setInterval(() => setElapsedMs(Date.now() - start), 100);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [status]);

  const formatTime = (ms: number) => {
    const secs = Math.floor(ms / 1000);
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const addActivity = useCallback((icon: string, label: string, detail: string, actStatus: ActivityEntry['status'] = 'done') => {
    const entry: ActivityEntry = {
      id: ++activityIdRef.current,
      icon,
      label,
      detail,
      status: actStatus,
      timestamp: new Date().toLocaleTimeString(),
    };
    setActivities(prev => [...prev, entry]);
    return entry.id;
  }, []);

  const updateActivity = useCallback((id: number, updates: Partial<ActivityEntry>) => {
    setActivities(prev => prev.map(a => a.id === id ? { ...a, ...updates } : a));
  }, []);

  // ── Advanced ATS Rewrite ──────────────────────────────────────
  const handleAdvancedRewrite = useCallback(async () => {
    if (!advanced) return;
    setRewriting(true);
    try {
      const result = await rewriteResume({
        job_id: job.id,
        github_url: github || undefined,
        linkedin_url: linkedin || undefined,
        advanced: true,
      });
      if (result.status === 'ok') {
        setRewriteResult(result.rewrite);
        setShowEditor(true);
      }
    } catch (e) {
      console.error('Rewrite failed:', e);
    } finally {
      setRewriting(false);
    }
  }, [advanced, job.id, github, linkedin]);

  // ── Start Apply — Real flow ──────────────────────────────────
  const handleStartApply = async () => {
    setStatus('verifying');
    setActivities([]);
    setElapsedMs(0);
    activityIdRef.current = 0;

    const verifyId = addActivity('🔍', 'URL Verification', 'Checking all candidate URLs for this job…', 'running');

    try {
      // Real API call — backend verifies all URLs, tries Gemini discovery, returns live-verified URL
      const res = await applyToJob(job.id);

      // Process verification steps from backend
      if (res.verification_steps) {
        for (const step of res.verification_steps) {
          const icon = step.status === 'complete' ? '✅' :
                       step.status === 'failed' ? '❌' :
                       step.status === 'skipped' ? '⏭️' : '⏳';
          const aStatus = step.status === 'complete' ? 'done' as const :
                          step.status === 'failed' ? 'error' as const :
                          step.status === 'skipped' ? 'skipped' as const : 'pending' as const;
          addActivity(icon, step.step, step.detail, aStatus);
        }
      }

      if (res.status === 'error' || res.error) {
        updateActivity(verifyId, { status: 'error', detail: res.error || 'No valid URL found' });
        setStatus('failed');
        addActivity('❌', 'Failed', res.error || 'No valid application URL available', 'error');
        return;
      }

      const resolvedUrl = res.apply_url || '';
      if (!resolvedUrl) {
        updateActivity(verifyId, { status: 'error', detail: 'No URL returned' });
        setStatus('failed');
        addActivity('❌', 'No URL', 'Backend could not resolve a valid apply URL', 'error');
        return;
      }

      updateActivity(verifyId, { status: 'done', detail: `Verified: ${resolvedUrl}` });
      setApplyUrl(resolvedUrl);
      setUrlSource(res.url_source || '');
      setLiveVerified(res.live_verified || false);

      // Transition to WebView
      setStatus('loading');
      addActivity('🌐', 'WebView', `Loading live page: ${resolvedUrl}`, 'running');

    } catch (e) {
      updateActivity(verifyId, { status: 'error', detail: String(e) });
      setStatus('failed');
      addActivity('❌', 'Error', `Apply failed: ${e instanceof Error ? e.message : 'Unknown error'}`, 'error');
    }
  };

  // When WebView reports state change
  const handleWebViewState = useCallback((state: 'loading' | 'loaded' | 'proxy' | 'failed') => {
    setWebViewState(state);
    if (state === 'loaded') {
      setStatus('live');
      addActivity('✅', 'Page Loaded', 'Company job page rendered in live WebView', 'done');
    } else if (state === 'proxy') {
      setStatus('live');
      addActivity('🔄', 'Proxy Rendered', 'Page loaded via secure CORS proxy', 'done');
    } else if (state === 'failed') {
      addActivity('⚠️', 'Embed Failed', 'Page blocks embedding — use direct link below', 'error');
    }
  }, [addActivity]);

  const handlePageTitle = useCallback((title: string) => {
    setPageTitle(title);
  }, []);

  // Open in new tab
  const handleOpenExternal = () => {
    if (applyUrl) {
      window.open(applyUrl, '_blank', 'noopener,noreferrer');
      addActivity('🔗', 'Opened External', `Opened ${applyUrl} in new tab`, 'done');
      setStatus('completed');
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'idle': return '#6b7280';
      case 'verifying': return '#f59e0b';
      case 'loading': return '#3b82f6';
      case 'live': return '#10b981';
      case 'completed': return '#059669';
      case 'failed': return '#ef4444';
    }
  };

  const getStatusLabel = () => {
    switch (status) {
      case 'idle': return '⏸ Ready';
      case 'verifying': return '🔍 Verifying URLs…';
      case 'loading': return '🌐 Loading page…';
      case 'live': return '✅ Live WebView';
      case 'completed': return '🎉 Done';
      case 'failed': return '❌ Failed';
    }
  };

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50"
        style={{ backgroundColor: 'rgba(0,0,0,0.88)', backdropFilter: 'blur(12px)' }}
      >
        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 30, scale: 0.97 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="live-apply-popup"
        >
          {/* ─── Header ─────────────────────────────────────── */}
          <div className="live-apply-header">
            <div className="live-apply-header-left">
              <div className="live-apply-status-dot" style={{ backgroundColor: getStatusColor() }} />
              <h2 className="live-apply-title">
                🤖 AI Apply — {job.company_name}
              </h2>
              <span className="live-apply-role">{job.role_title}</span>
              {liveVerified && (
                <span className="live-apply-verified-badge">✓ Live Verified</span>
              )}
            </div>
            <div className="live-apply-header-right">
              <span className="live-apply-timer">{formatTime(elapsedMs)}</span>
              <span className="live-apply-status-label" style={{ color: getStatusColor() }}>
                {getStatusLabel()}
              </span>
              <button onClick={onClose} className="live-apply-close" title="Close">✕</button>
            </div>
          </div>

          {/* ─── Body — 3 Panels ────────────────────────────── */}
          <div className="live-apply-body">

            {/* LEFT PANEL — Profile & Controls */}
            <div className="live-apply-panel-left">
              <h3 className="live-apply-panel-title">Profile</h3>
              <div className="live-apply-form">
                <div className="live-apply-field">
                  <label>Full Name</label>
                  <input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Jane Doe" />
                </div>
                <div className="live-apply-field">
                  <label>Email</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="jane@example.com" />
                </div>
                <div className="live-apply-field">
                  <label>Phone</label>
                  <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="+91 98765 43210" />
                </div>
                <div className="live-apply-field">
                  <label>LinkedIn</label>
                  <input value={linkedin} onChange={e => setLinkedin(e.target.value)} placeholder="linkedin.com/in/..." />
                </div>
                <div className="live-apply-field">
                  <label>GitHub</label>
                  <input value={github} onChange={e => setGithub(e.target.value)} placeholder="github.com/..." />
                </div>
                <div className="live-apply-field">
                  <label>Resume</label>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={e => setResumeFile(e.target.files?.[0] || null)}
                    className="live-apply-file-input"
                  />
                  {resumeFile && <span className="live-apply-file-name">📎 {resumeFile.name}</span>}
                </div>

                {/* Advanced ATS Toggle */}
                <div className="live-apply-advanced-toggle">
                  <label className="live-apply-toggle-label">
                    <input
                      type="checkbox"
                      checked={advanced}
                      onChange={e => setAdvanced(e.target.checked)}
                    />
                    <span className="live-apply-toggle-slider" />
                    <span>ATS Optimization</span>
                  </label>
                  {advanced && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      className="live-apply-advanced-info"
                    >
                      <p>AI rewrites your resume to match this JD's ATS keywords.</p>
                      <button
                        onClick={handleAdvancedRewrite}
                        disabled={rewriting}
                        className="live-apply-rewrite-btn"
                      >
                        {rewriting ? '✍️ Rewriting...' : '✨ Preview Rewrite'}
                      </button>
                    </motion.div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="live-apply-actions">
                  {status === 'idle' && (
                    <button onClick={handleStartApply} className="live-apply-start-btn">
                      🤖 Start AI Apply
                    </button>
                  )}
                  {(status === 'live' || status === 'loading') && (
                    <button onClick={handleOpenExternal} className="live-apply-external-btn">
                      🔗 Open in New Tab
                    </button>
                  )}
                  {status === 'failed' && applyUrl && (
                    <button onClick={handleOpenExternal} className="live-apply-external-btn">
                      🔗 Open Direct Link
                    </button>
                  )}
                  {status === 'failed' && !applyUrl && (
                    <button onClick={handleStartApply} className="live-apply-retry-btn">
                      🔄 Retry
                    </button>
                  )}
                  {status === 'completed' && (
                    <div className="live-apply-completed-msg">
                      ✅ Application page opened successfully
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* CENTER PANEL — Live WebView */}
            <div className="live-apply-panel-center">
              {/* URL Bar */}
              <div className="live-apply-url-bar">
                <div className="live-apply-url-bar-icon">
                  {status === 'live' ? '🔒' : status === 'verifying' ? '🔍' : '🌐'}
                </div>
                <div className="live-apply-url-text">
                  {applyUrl || (status === 'verifying' ? 'Verifying URLs…' : 'Click "Start AI Apply" to begin')}
                </div>
                {urlSource && (
                  <div className="live-apply-url-source">
                    via {urlSource.replace('_', ' ')}
                  </div>
                )}
              </div>

              {/* WebView / States */}
              <div className="live-apply-canvas-wrapper">
                {status === 'idle' ? (
                  <div className="live-apply-idle-state">
                    <div className="live-apply-idle-icon">🤖</div>
                    <p className="live-apply-idle-title">Ready to Apply</p>
                    <p className="live-apply-idle-subtitle">
                      Fill in your profile and click "Start AI Apply" to load the live application page
                    </p>
                  </div>
                ) : status === 'verifying' ? (
                  <div className="live-apply-idle-state">
                    <div className="live-apply-verifying-spinner" />
                    <p className="live-apply-idle-title">Verifying Application URLs</p>
                    <p className="live-apply-idle-subtitle">
                      Checking job URL, source URL, and AI-discovered URLs…
                    </p>
                  </div>
                ) : status === 'failed' && !applyUrl ? (
                  <div className="live-apply-idle-state">
                    <div className="live-apply-idle-icon">❌</div>
                    <p className="live-apply-idle-title">No Valid URL Found</p>
                    <p className="live-apply-idle-subtitle">
                      All candidate URLs are unreachable. Try the company website directly.
                    </p>
                    {job.company_website && (
                      <a
                        href={job.company_website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="live-apply-fallback-link"
                      >
                        🔗 Visit {job.company_name} website
                      </a>
                    )}
                  </div>
                ) : applyUrl ? (
                  <WebViewFrame
                    url={applyUrl}
                    onPageTitleChange={handlePageTitle}
                    onLoadStateChange={handleWebViewState}
                  />
                ) : null}
              </div>

              {/* Status Bar */}
              <div className="live-apply-status-bar">
                <span>{pageTitle || job.company_name}</span>
                <span className="live-apply-status-badge" style={{ color: getStatusColor() }}>
                  {getStatusLabel()}
                </span>
              </div>
            </div>

            {/* RIGHT PANEL — Activity Log */}
            <div className="live-apply-panel-right">
              <h3 className="live-apply-panel-title">Activity Log</h3>
              <div className="live-apply-step-log">
                {activities.length === 0 && (
                  <div className="live-apply-step-empty">
                    <p>Real-time verification events will appear here.</p>
                  </div>
                )}
                {activities.map(entry => (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`live-apply-step ${entry.status === 'running' ? 'step-active' : ''}`}
                  >
                    <span className="live-apply-step-icon">{entry.icon}</span>
                    <div className="live-apply-step-content">
                      <span className={`live-apply-step-action step-status-${entry.status}`}>
                        {entry.label}
                      </span>
                      <span className="live-apply-step-target">{entry.detail}</span>
                    </div>
                    <span className="live-apply-step-time">{entry.timestamp}</span>
                  </motion.div>
                ))}
                <div ref={stepsEndRef} />
              </div>
            </div>
          </div>

          {/* ─── Resume Editor Overlay ────────────────────── */}
          <AnimatePresence>
            {showEditor && rewriteResult && (
              <motion.div
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 40 }}
                className="live-apply-editor-overlay"
              >
                <div className="live-apply-editor">
                  <div className="live-apply-editor-header">
                    <h3>✨ ATS-Optimized Resume Preview</h3>
                    <div className="live-apply-editor-scores">
                      <span className="score-before">Before: {rewriteResult.ats_score_before}%</span>
                      <span className="score-arrow">→</span>
                      <span className="score-after">After: {rewriteResult.ats_score_after}%</span>
                    </div>
                    <button onClick={() => setShowEditor(false)} className="live-apply-editor-close">✕</button>
                  </div>
                  <div className="live-apply-editor-body">
                    {rewriteResult.sections.map((section, i) => (
                      <div key={i} className="live-apply-editor-section">
                        <h4>{section.name}</h4>
                        <div className="live-apply-editor-diff">
                          <div className="diff-panel diff-original">
                            <h5>Original</h5>
                            <pre>{section.original}</pre>
                          </div>
                          <div className="diff-panel diff-rewritten">
                            <h5>Optimized</h5>
                            <pre>{section.rewritten}</pre>
                          </div>
                        </div>
                        {section.changes.length > 0 && (
                          <div className="diff-changes">
                            {section.changes.map((change, j) => (
                              <span key={j} className={`diff-badge diff-${change.type}`}>
                                {change.type === 'add' && '+ '}
                                {change.type === 'remove' && '- '}
                                {change.type === 'modify' && '~ '}
                                {change.after || change.before}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                    {rewriteResult.keywords_added.length > 0 && (
                      <div className="live-apply-editor-keywords">
                        <h5>Keywords Added</h5>
                        <div className="keyword-tags">
                          {rewriteResult.keywords_added.map((kw, i) => (
                            <span key={i} className="keyword-tag">{kw}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="live-apply-editor-footer">
                    <button onClick={() => setShowEditor(false)} className="live-apply-approve-btn">
                      ✅ Approve & Continue
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
