/* ═══════════════════════════════════════════════════════════════
   LiveAutoApplyDashboard — 3-Panel Real-Time Auto-Apply Dashboard
   Panel A: Job Queue (left)
   Panel B: Active Browser Viewer (center)  
   Panel C: Application Evidence (right)
   ═══════════════════════════════════════════════════════════════ */
import { useState, useEffect, useCallback, useRef } from 'react';
import BrowserViewer from './BrowserViewer';
import type { BrowserSessionState, AutomationStep } from './BrowserViewer';
import {
  getDashboardStats,
  getApplications,
  getAutoApplyConfig,
  saveAutoApplyConfig,
  runAutoApply,
  updateApplicationStatus,
  getProfile,
  saveProfile,
} from '../api';
import type { DashboardStats, ApplicationRecord, AutoApplyConfig, ApplicationProfile } from '../types';

/* ── Queue Job type ──────────────────────────────────────────── */
interface QueuedJob {
  id: string;
  companyName: string;
  companyLogo: string;
  roleTitle: string;
  careersUrl: string;
  status: 'queued' | 'in_progress' | 'applied' | 'needs_review' | 'failed' | 'skipped';
  queuedAt: string;
  completedAt?: string;
  matchScore: number;
  tags: string[];
  progress?: { current: number; total: number };
  previewScreenshot?: string;
}

/* ── Evidence type ───────────────────────────────────────────── */
interface ApplicationEvidence {
  id: string;
  companyName: string;
  roleTitle: string;
  careersUrl: string;
  confirmationText?: string;
  confirmationNumber?: string;
  screenshotUrl?: string;
  stepLog: AutomationStep[];
  submittedAt: string;
  emailStatus: 'sent' | 'pending' | 'failed';
  totalTime: number;
  userIntervened: boolean;
  interventionStep?: number;
}

/* ── Status config ───────────────────────────────────────────── */
const STATUS_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  queued: { icon: '⏳', color: '#6b7280', label: 'Queued' },
  in_progress: { icon: '🔄', color: '#14b8a6', label: 'In Progress' },
  applied: { icon: '✅', color: '#10b981', label: 'Applied' },
  needs_review: { icon: '⚠️', color: '#f59e0b', label: 'Needs Review' },
  failed: { icon: '❌', color: '#ef4444', label: 'Failed' },
  skipped: { icon: '⏭️', color: '#6b7280', label: 'Skipped' },
};

/* ── Sound helper ────────────────────────────────────────────── */
function playNotificationSound(type: 'success' | 'warning' | 'error') {
  try {
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    gain.gain.value = 0.1;
    
    if (type === 'success') {
      osc.frequency.value = 880;
      osc.type = 'sine';
    } else if (type === 'warning') {
      osc.frequency.value = 660;
      osc.type = 'triangle';
    } else {
      osc.frequency.value = 300;
      osc.type = 'sawtooth';
    }
    
    osc.start();
    osc.stop(audioCtx.currentTime + 0.15);
  } catch {}
}

export default function LiveAutoApplyDashboard() {
  // ── State ──────────────────────────────────────────────────
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [config, setConfig] = useState<AutoApplyConfig>({
    enabled: false, startup_only: true, india_only: false, remote_india: true,
    engineering_only: true, min_match_score: 40, salary_min: null, max_days_old: 30,
    whitelist_companies: [], blacklist_companies: [], approval_mode: 'approval',
    max_daily_applications: 25, paused: false,
  });
  const [profile, setProfile] = useState<ApplicationProfile>({
    full_name: '', email: '', phone: '', location: '', work_authorization: '',
    notice_period: '', years_of_experience: 0, linkedin_url: '', github_url: '',
    portfolio_url: '', resume_text: '', cover_letter_template: '',
    preferred_titles: [], preferred_cities: [], preferred_stages: [],
    preferred_tech_stack: [], remote_preference: 'any', salary_expectation: '',
    blacklist_companies: [], blacklist_domains: [], include_stealth: true,
    auto_apply_mode: 'manual',
  });

  const [activeTab, setActiveTab] = useState<'live' | 'overview' | 'applications' | 'config' | 'profile'>('live');
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState('');
  const [saving, setSaving] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedApp, setExpandedApp] = useState<string | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null);

  // ── Queue state ────────────────────────────────────────────
  const [jobQueue, setJobQueue] = useState<QueuedJob[]>([]);
  const [activeSession, setActiveSession] = useState<BrowserSessionState | null>(null);
  const [evidenceList, setEvidenceList] = useState<ApplicationEvidence[]>([]);
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);

  // ── Polling / WebSocket for real-time updates ──────────────
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // ── Data loading ───────────────────────────────────────────
  const load = useCallback(async () => {
    try {
      const [s, a, c, p] = await Promise.all([
        getDashboardStats(), getApplications(), getAutoApplyConfig(), getProfile(),
      ]);
      if (s?.stats) setStats(s.stats);
      if (a?.applications) setApplications(a.applications);
      if (c?.config) setConfig(c.config);
      if (p?.profile) setProfile(p.profile);
    } catch (e) { console.error('Dashboard load error', e); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // WebSocket for real-time automation events
  useEffect(() => {
    const connectWs = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.hostname}:8000/ws/auto-apply`);
        wsRef.current = ws;

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            
            switch (msg.type) {
              case 'queue_update':
                setJobQueue(msg.queue || []);
                break;
              case 'session_update':
                setActiveSession(msg.session);
                break;
              case 'step_added':
                setActiveSession(prev => prev ? {
                  ...prev,
                  steps: [...prev.steps, msg.step],
                  elapsedMs: msg.elapsedMs || prev.elapsedMs,
                  mouseX: msg.mouseX ?? prev.mouseX,
                  mouseY: msg.mouseY ?? prev.mouseY,
                  currentUrl: msg.currentUrl || prev.currentUrl,
                  pageTitle: msg.pageTitle || prev.pageTitle,
                  progress: msg.progress || prev.progress,
                } : null);
                break;
              case 'application_complete':
                if (soundEnabled) playNotificationSound('success');
                setEvidenceList(prev => [msg.evidence, ...prev]);
                load(); // refresh stats
                break;
              case 'needs_intervention':
                if (soundEnabled) playNotificationSound('warning');
                break;
              case 'application_failed':
                if (soundEnabled) playNotificationSound('error');
                break;
              case 'status_change':
                setJobQueue(prev => prev.map(j => 
                  j.id === msg.jobId ? { ...j, status: msg.newStatus } : j
                ));
                break;
            }
          } catch {}
        };

        ws.onclose = () => {
          setTimeout(connectWs, 3000);
        };
      } catch {}
    };

    connectWs();

    // Also poll for updates as fallback
    pollRef.current = setInterval(() => {
      load();
    }, 5000);

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [load, soundEnabled]);

  // ── Handlers ───────────────────────────────────────────────
  const handleRun = async () => {
    setIsRunning(true);
    setRunResult('');
    try {
      const r = await runAutoApply();
      setRunResult(`✅ Matched ${r.matched || 0} jobs — ${r.applied || 0} applied, ${r.needs_review || 0} need review`);
      load();
    } catch {
      setRunResult('❌ Auto-apply failed');
    }
    setIsRunning(false);
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    await saveAutoApplyConfig(config);
    setSaving(false);
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    await saveProfile(profile);
    setSaving(false);
  };

  const handleStatusUpdate = async (appId: string, newStatus: string) => {
    await updateApplicationStatus(appId, newStatus);
    load();
  };

  const handleTakeControl = () => {
    setActiveSession(prev => prev ? { ...prev, status: 'user_control' } : null);
    // Send to backend via WS
    wsRef.current?.send(JSON.stringify({ type: 'take_control' }));
  };

  const handleResumeAutomation = () => {
    setActiveSession(prev => prev ? { ...prev, status: 'running' } : null);
    wsRef.current?.send(JSON.stringify({ type: 'resume_automation' }));
  };

  const handleMarkSubmitted = () => {
    wsRef.current?.send(JSON.stringify({ type: 'mark_submitted' }));
  };

  const handleStopAll = () => {
    wsRef.current?.send(JSON.stringify({ type: 'stop_all' }));
    setActiveSession(null);
    setJobQueue(prev => prev.map(j => 
      j.status === 'in_progress' || j.status === 'queued'
        ? { ...j, status: 'skipped' }
        : j
    ));
  };

  const handleRemoveFromQueue = (jobId: string) => {
    setJobQueue(prev => prev.filter(j => j.id !== jobId));
    wsRef.current?.send(JSON.stringify({ type: 'remove_job', jobId }));
  };

  // ── Drag-and-drop reorder ──────────────────────────────────
  const handleDragStart = (idx: number) => setDraggedIdx(idx);
  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (draggedIdx === null || draggedIdx === idx) return;
    setJobQueue(prev => {
      const queue = [...prev];
      const [removed] = queue.splice(draggedIdx, 1);
      queue.splice(idx, 0, removed);
      return queue;
    });
    setDraggedIdx(idx);
  };
  const handleDragEnd = () => setDraggedIdx(null);

  const filteredApps = statusFilter
    ? applications.filter(a => a.status === statusFilter)
    : applications;

  const timeAgo = (iso: string) => {
    try {
      const diff = Date.now() - new Date(iso).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 60) return `${mins}m ago`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}h ago`;
      return `${Math.floor(hrs / 24)}d ago`;
    } catch { return iso; }
  };

  // Sort queue: in_progress first, then queued, then completed
  const sortedQueue = [...jobQueue].sort((a, b) => {
    const order: Record<string, number> = { in_progress: 0, queued: 1, needs_review: 2, applied: 3, failed: 4, skipped: 5 };
    return (order[a.status] ?? 3) - (order[b.status] ?? 3);
  });

  // ═════════════════════════════════════════════════════════════
  // RENDER
  // ═════════════════════════════════════════════════════════════
  return (
    <div className="la-dashboard">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="la-header">
        <div className="la-header-left">
          <h1 className="la-title">🚀 Auto-Apply Dashboard</h1>
          <p className="la-subtitle">Real-Time Browser Automation & Application Tracking</p>
        </div>
        <div className="la-header-right">
          <label className="la-sound-toggle" title="Toggle notification sounds">
            <input
              type="checkbox"
              checked={soundEnabled}
              onChange={() => setSoundEnabled(!soundEnabled)}
            />
            {soundEnabled ? '🔊' : '🔇'}
          </label>
          {(activeSession && activeSession.status !== 'completed' && activeSession.status !== 'failed') && (
            <button className="la-stop-all-btn" onClick={handleStopAll}>
              ⏹ Stop All
            </button>
          )}
          <button
            className={`la-run-btn ${isRunning ? 'running' : ''}`}
            onClick={handleRun}
            disabled={isRunning}
          >
            {isRunning ? '⏳ Running…' : '▶ Run Auto-Apply'}
          </button>
        </div>
      </div>
      {runResult && <div className="la-run-result">{runResult}</div>}

      {/* ── Tabs ────────────────────────────────────────────── */}
      <div className="la-tabs">
        {(['live', 'overview', 'applications', 'config', 'profile'] as const).map(tab => (
          <button
            key={tab}
            className={`la-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'live' ? '🖥️ Live View' :
             tab === 'overview' ? '📊 Overview' :
             tab === 'applications' ? '📋 Applications' :
             tab === 'config' ? '⚙️ Config' : '👤 Profile'}
          </button>
        ))}
      </div>

      {/* ═══ LIVE VIEW — 3-Panel Layout ═══════════════════════ */}
      {activeTab === 'live' && (
        <div className="la-live-grid">
          {/* ── Panel A: Job Queue ──────────────────────────── */}
          <div className="la-panel la-panel-queue">
            <div className="la-panel-header">
              <h3 className="la-panel-title">📋 Job Queue</h3>
              <span className="la-panel-count">{sortedQueue.length}</span>
            </div>
            <div className="la-queue-list">
              {sortedQueue.length === 0 ? (
                <div className="la-queue-empty">
                  <p>No jobs queued</p>
                  <p className="la-queue-empty-hint">Run Auto-Apply to queue matching jobs</p>
                </div>
              ) : (
                sortedQueue.map((job, idx) => {
                  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.queued;
                  const isActive = job.status === 'in_progress';
                  return (
                    <div
                      key={job.id}
                      className={`la-queue-card ${isActive ? 'la-queue-active' : ''} la-queue-${job.status}`}
                      draggable={job.status === 'queued'}
                      onDragStart={() => handleDragStart(idx)}
                      onDragOver={(e) => handleDragOver(e, idx)}
                      onDragEnd={handleDragEnd}
                    >
                      <div className="la-queue-card-top">
                        <div className="la-queue-company-info">
                          {job.companyLogo ? (
                            <img
                              src={job.companyLogo}
                              alt=""
                              className="la-queue-logo"
                              onError={(e) => {
                                (e.target as HTMLImageElement).style.display = 'none';
                              }}
                            />
                          ) : (
                            <div className="la-queue-logo-placeholder">
                              {job.companyName.charAt(0)}
                            </div>
                          )}
                          <div className="la-queue-text">
                            <div className="la-queue-role">{job.roleTitle}</div>
                            <div className="la-queue-company">{job.companyName}</div>
                          </div>
                        </div>
                        <div className={`la-queue-status-dot`} style={{ color: cfg.color }}>
                          {cfg.icon}
                        </div>
                      </div>
                      
                      {/* Progress bar for in-progress */}
                      {isActive && job.progress && (
                        <div className="la-queue-progress">
                          <div
                            className="la-queue-progress-fill"
                            style={{ width: `${(job.progress.current / Math.max(job.progress.total, 1)) * 100}%` }}
                          />
                          <span className="la-queue-progress-text">
                            Step {job.progress.current}/{job.progress.total}
                          </span>
                        </div>
                      )}

                      <div className="la-queue-card-bottom">
                        <div className="la-queue-meta">
                          {job.matchScore > 0 && (
                            <span className="la-queue-match">{job.matchScore}% match</span>
                          )}
                          <span className="la-queue-time">{timeAgo(job.queuedAt)}</span>
                        </div>
                        <div className="la-queue-tags">
                          {job.tags.slice(0, 3).map((tag, i) => (
                            <span key={i} className="la-queue-tag">{tag}</span>
                          ))}
                        </div>
                      </div>

                      {/* Careers URL */}
                      <a
                        href={job.careersUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="la-queue-url"
                        onClick={e => e.stopPropagation()}
                      >
                        🔗 {new URL(job.careersUrl || 'https://unknown.com').hostname}
                      </a>

                      {/* Remove button for queued jobs */}
                      {job.status === 'queued' && (
                        <button
                          className="la-queue-remove"
                          onClick={() => handleRemoveFromQueue(job.id)}
                          title="Remove from queue"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* ── Panel B: Active Browser Viewer ──────────────── */}
          <div className="la-panel la-panel-viewer">
            <BrowserViewer
              session={activeSession}
              onTakeControl={handleTakeControl}
              onResumeAutomation={handleResumeAutomation}
              onMarkSubmitted={handleMarkSubmitted}
              onStopAll={handleStopAll}
            />
          </div>

          {/* ── Panel C: Application Evidence ──────────────── */}
          <div className="la-panel la-panel-evidence">
            <div className="la-panel-header">
              <h3 className="la-panel-title">📄 Evidence</h3>
              <span className="la-panel-count">{evidenceList.length}</span>
            </div>
            <div className="la-evidence-list">
              {evidenceList.length === 0 ? (
                <div className="la-evidence-empty">
                  <p>No completed applications yet</p>
                  <p className="la-evidence-empty-hint">Evidence will appear here after each submission</p>
                </div>
              ) : (
                evidenceList.map((ev) => (
                  <div
                    key={ev.id}
                    className={`la-evidence-card ${expandedEvidence === ev.id ? 'expanded' : ''}`}
                    onClick={() => setExpandedEvidence(expandedEvidence === ev.id ? null : ev.id)}
                  >
                    <div className="la-evidence-top">
                      <div className="la-evidence-info">
                        <div className="la-evidence-role">{ev.roleTitle}</div>
                        <div className="la-evidence-company">{ev.companyName}</div>
                      </div>
                      <div className="la-evidence-meta">
                        <span className={`la-evidence-email-status ${ev.emailStatus}`}>
                          {ev.emailStatus === 'sent' ? '📧 Sent' :
                           ev.emailStatus === 'pending' ? '⏳ Pending' : '❌ Failed'}
                        </span>
                        <span className="la-evidence-time">{timeAgo(ev.submittedAt)}</span>
                      </div>
                    </div>
                    
                    {expandedEvidence === ev.id && (
                      <div className="la-evidence-details">
                        {/* Careers page URL */}
                        <div className="la-evidence-row">
                          <span className="la-evidence-label">🔗 Careers URL</span>
                          <a href={ev.careersUrl} target="_blank" rel="noopener noreferrer" className="la-evidence-link">
                            {ev.careersUrl}
                          </a>
                        </div>

                        {/* Confirmation */}
                        {ev.confirmationText && (
                          <div className="la-evidence-row">
                            <span className="la-evidence-label">✅ Confirmation</span>
                            <span className="la-evidence-value">{ev.confirmationText}</span>
                          </div>
                        )}
                        {ev.confirmationNumber && (
                          <div className="la-evidence-row">
                            <span className="la-evidence-label"># Number</span>
                            <span className="la-evidence-value">{ev.confirmationNumber}</span>
                          </div>
                        )}

                        {/* Screenshot */}
                        {ev.screenshotUrl && (
                          <div className="la-evidence-screenshot-wrapper">
                            <img
                              src={ev.screenshotUrl}
                              alt="Confirmation screenshot"
                              className="la-evidence-screenshot"
                              onClick={(e) => {
                                e.stopPropagation();
                                window.open(ev.screenshotUrl, '_blank');
                              }}
                            />
                          </div>
                        )}

                        {/* Step log download */}
                        <div className="la-evidence-actions">
                          <button
                            className="la-evidence-download"
                            onClick={(e) => {
                              e.stopPropagation();
                              const log = ev.stepLog.map(s =>
                                `[${String(s.stepNumber).padStart(2, '0')}] ${s.timestamp}  ${s.actionType.padEnd(12)} → ${s.target}${s.value ? ` = "${s.value}"` : ''}`
                              ).join('\n');
                              const blob = new Blob([log], { type: 'text/plain' });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `steplog-${ev.companyName}-${ev.roleTitle}.txt`;
                              a.click();
                              URL.revokeObjectURL(url);
                            }}
                          >
                            📥 Download Step Log
                          </button>
                        </div>

                        {/* Time and intervention info */}
                        <div className="la-evidence-footer">
                          <span>⏱️ {Math.round(ev.totalTime / 1000)}s total</span>
                          {ev.userIntervened && (
                            <span className="la-evidence-intervened">
                              🎮 User intervened at step {ev.interventionStep}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
            
            {/* Export buttons */}
            {evidenceList.length > 0 && (
              <div className="la-evidence-export">
                <button className="la-export-btn" onClick={() => {
                  const csv = [
                    'Company,Role,URL,Status,Confirmation,Submitted At,Email Status,Duration (s)',
                    ...evidenceList.map(ev =>
                      `"${ev.companyName}","${ev.roleTitle}","${ev.careersUrl}","Applied","${ev.confirmationText || ''}","${ev.submittedAt}","${ev.emailStatus}","${Math.round(ev.totalTime/1000)}"`
                    )
                  ].join('\n');
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'application-evidence.csv';
                  a.click();
                }}>
                  📊 Export CSV
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ OVERVIEW TAB ═════════════════════════════════════ */}
      {activeTab === 'overview' && stats && (
        <div className="la-overview">
          <div className="la-stats-grid">
            <StatCard icon="💼" label="Total Jobs" value={stats.total_jobs} color="#6366f1" />
            <StatCard icon="🚀" label="Startup Jobs" value={stats.total_startup_jobs} sub={`${stats.startup_percentage}%`} color="#059669" />
            <StatCard icon="🔒" label="Stealth" value={stats.stealth_jobs} color="#7c3aed" />
            <StatCard icon="🇮🇳" label="India Jobs" value={stats.india_jobs} color="#f59e0b" />
            <StatCard icon="🔧" label="Engineering" value={stats.engineering_jobs} color="#3b82f6" />
            <StatCard icon="🌍" label="Relocation" value={stats.relocation_jobs} color="#10b981" />
            <StatCard icon="⚡" label="Auto-Eligible" value={stats.auto_apply_eligible} color="#8b5cf6" />
            <StatCard icon="✅" label="Applied" value={stats.applications_sent} color="#16a34a" />
            <StatCard icon="⏳" label="Pending" value={stats.pending_approvals} color="#f59e0b" />
            <StatCard icon="❌" label="Failed" value={stats.failed_applications} color="#dc2626" />
            <StatCard icon="📧" label="Emails Sent" value={stats.emails_sent} color="#6366f1" />
          </div>
          {/* Top Tech Stacks */}
          <div className="la-section">
            <h3 className="la-section-title">🏷️ Top Startup Tech Stacks</h3>
            <div className="la-tags-cloud">
              {stats.top_tech_stacks.map((t, i) => (
                <span key={i} className="la-tech-tag" style={{ opacity: 0.6 + (t.count / (stats.top_tech_stacks[0]?.count || 1)) * 0.4 }}>
                  {t.name} <span className="la-tag-count">{t.count}</span>
                </span>
              ))}
            </div>
          </div>
          {/* Top Domains */}
          <div className="la-section">
            <h3 className="la-section-title">🏢 Top Startup Domains</h3>
            <div className="la-domain-bars">
              {stats.top_startup_domains.slice(0, 8).map((d, i) => (
                <div key={i} className="la-domain-row">
                  <span className="la-domain-name">{d.name}</span>
                  <div className="la-domain-bar-bg">
                    <div className="la-domain-bar-fill" style={{ width: `${(d.count / (stats.top_startup_domains[0]?.count || 1)) * 100}%` }} />
                  </div>
                  <span className="la-domain-count">{d.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ═══ APPLICATIONS TAB ═════════════════════════════════ */}
      {activeTab === 'applications' && (
        <div className="la-applications">
          <div className="la-app-filters">
            {['', 'Applied', 'Pending', 'Needs Review', 'Failed', 'Skipped'].map(s => (
              <button key={s} className={`la-filter-btn ${statusFilter === s ? 'active' : ''}`} onClick={() => setStatusFilter(s)}>
                {s || 'All'} {s ? `(${applications.filter(a => a.status === s).length})` : `(${applications.length})`}
              </button>
            ))}
          </div>
          {filteredApps.length === 0 ? (
            <div className="la-empty">No applications yet. Run Auto-Apply or apply to jobs from the board.</div>
          ) : (
            <div className="la-app-list">
              {filteredApps.map(app => (
                <div key={app.id} className={`la-app-card ${app.status.toLowerCase().replace(' ', '-')}`}>
                  <div className="la-app-main" onClick={() => setExpandedApp(expandedApp === app.id ? null : app.id)}>
                    <div className="la-app-info">
                      <h4 className="la-app-role">{app.role_title}</h4>
                      <p className="la-app-company">{app.company_name}</p>
                    </div>
                    <div className="la-app-meta">
                      <span className={`la-app-status ${app.status.toLowerCase().replace(' ', '-')}`}>{app.status}</span>
                      <span className="la-app-method">{app.method === 'auto' ? '🤖' : app.method === 'one_click' ? '⚡' : '🔗'} {app.method}</span>
                      <span className="la-app-time">{timeAgo(app.applied_at)}</span>
                      {app.email_sent && <span className="la-app-email-badge">📧</span>}
                    </div>
                  </div>
                  {expandedApp === app.id && (
                    <div className="la-app-details">
                      <div className="la-app-steps">
                        {app.steps.map((step, i) => (
                          <div key={i} className={`la-step ${step.status}`}>
                            <span className="la-step-icon">
                              {step.status === 'complete' ? '✅' : step.status === 'pending' ? '⏳' : '⏭️'}
                            </span>
                            <div className="la-step-content">
                              <strong>{step.step}</strong>
                              <p>{step.detail}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                      {app.apply_url && (
                        <a href={app.apply_url} target="_blank" rel="noopener noreferrer" className="la-open-link">🔗 Open Application Page</a>
                      )}
                      <div className="la-app-actions">
                        {app.status === 'Needs Review' && (
                          <button className="la-approve-btn" onClick={() => handleStatusUpdate(app.id, 'Applied')}>✅ Approve</button>
                        )}
                        {app.status !== 'Skipped' && app.status !== 'Applied' && (
                          <button className="la-skip-btn" onClick={() => handleStatusUpdate(app.id, 'Skipped')}>⏭️ Skip</button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══ CONFIG TAB ═══════════════════════════════════════ */}
      {activeTab === 'config' && (
        <div className="la-config">
          <h3 className="la-section-title">⚙️ Auto-Apply Configuration</h3>
          <div className="la-config-grid">
            <ToggleField label="Enable Auto-Apply" value={config.enabled} onChange={v => setConfig({ ...config, enabled: v })} />
            <ToggleField label="Startup Jobs Only" value={config.startup_only} onChange={v => setConfig({ ...config, startup_only: v })} />
            <ToggleField label="India Only" value={config.india_only} onChange={v => setConfig({ ...config, india_only: v })} />
            <ToggleField label="Remote India" value={config.remote_india} onChange={v => setConfig({ ...config, remote_india: v })} />
            <ToggleField label="Engineering Only" value={config.engineering_only} onChange={v => setConfig({ ...config, engineering_only: v })} />
            <ToggleField label="Paused" value={config.paused} onChange={v => setConfig({ ...config, paused: v })} />
            <div className="la-config-field">
              <label>Min Match Score</label>
              <input type="range" min={0} max={100} value={config.min_match_score} onChange={e => setConfig({ ...config, min_match_score: +e.target.value })} />
              <span className="la-range-value">{config.min_match_score}%</span>
            </div>
            <div className="la-config-field">
              <label>Max Daily Applications</label>
              <input type="number" min={1} max={50} value={config.max_daily_applications} onChange={e => setConfig({ ...config, max_daily_applications: +e.target.value })} />
            </div>
            <div className="la-config-field">
              <label>Max Days Old</label>
              <input type="number" min={1} max={90} value={config.max_days_old} onChange={e => setConfig({ ...config, max_days_old: +e.target.value })} />
            </div>
            <div className="la-config-field">
              <label>Approval Mode</label>
              <select value={config.approval_mode} onChange={e => setConfig({ ...config, approval_mode: e.target.value })}>
                <option value="approval">Approval Required</option>
                <option value="one_click">One-Click</option>
                <option value="batch">Batch Approval</option>
                <option value="automatic">Fully Automatic</option>
              </select>
            </div>
          </div>
          <button className="la-save-btn" onClick={handleSaveConfig} disabled={saving}>
            {saving ? 'Saving…' : '💾 Save Configuration'}
          </button>
        </div>
      )}

      {/* ═══ PROFILE TAB ══════════════════════════════════════ */}
      {activeTab === 'profile' && (
        <div className="la-profile">
          <h3 className="la-section-title">👤 Application Profile</h3>
          <p className="la-profile-hint">This information is used to pre-fill applications and send confirmation emails.</p>
          <div className="la-profile-grid">
            <ProfileField label="Full Name" value={profile.full_name} onChange={v => setProfile({ ...profile, full_name: v })} />
            <ProfileField label="Email" value={profile.email} onChange={v => setProfile({ ...profile, email: v })} type="email" />
            <ProfileField label="Phone" value={profile.phone} onChange={v => setProfile({ ...profile, phone: v })} />
            <ProfileField label="Location" value={profile.location} onChange={v => setProfile({ ...profile, location: v })} />
            <ProfileField label="Work Authorization" value={profile.work_authorization} onChange={v => setProfile({ ...profile, work_authorization: v })} />
            <ProfileField label="Notice Period" value={profile.notice_period} onChange={v => setProfile({ ...profile, notice_period: v })} />
            <ProfileField label="Years of Experience" value={String(profile.years_of_experience)} onChange={v => setProfile({ ...profile, years_of_experience: +v })} type="number" />
            <ProfileField label="LinkedIn URL" value={profile.linkedin_url} onChange={v => setProfile({ ...profile, linkedin_url: v })} />
            <ProfileField label="GitHub URL" value={profile.github_url} onChange={v => setProfile({ ...profile, github_url: v })} />
            <ProfileField label="Portfolio URL" value={profile.portfolio_url} onChange={v => setProfile({ ...profile, portfolio_url: v })} />
            <ProfileField label="Salary Expectation" value={profile.salary_expectation} onChange={v => setProfile({ ...profile, salary_expectation: v })} />
            <div className="la-profile-field full-width">
              <label>Preferred Cities</label>
              <input value={profile.preferred_cities.join(', ')} onChange={e => setProfile({ ...profile, preferred_cities: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
            <div className="la-profile-field full-width">
              <label>Preferred Tech Stack</label>
              <input value={profile.preferred_tech_stack.join(', ')} onChange={e => setProfile({ ...profile, preferred_tech_stack: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
            <div className="la-profile-field full-width">
              <label>Blacklist Companies</label>
              <input value={profile.blacklist_companies.join(', ')} onChange={e => setProfile({ ...profile, blacklist_companies: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
          </div>
          <button className="la-save-btn" onClick={handleSaveProfile} disabled={saving}>
            {saving ? 'Saving…' : '💾 Save Profile'}
          </button>
        </div>
      )}
    </div>
  );
}

/* ══ Sub-components ══════════════════════════════════════════ */

function StatCard({ icon, label, value, sub, color }: { icon: string; label: string; value: number; sub?: string; color: string }) {
  return (
    <div className="la-stat-card" style={{ borderTop: `3px solid ${color}` }}>
      <span className="la-stat-icon">{icon}</span>
      <div className="la-stat-value">{value.toLocaleString()}</div>
      <div className="la-stat-label">{label}</div>
      {sub && <div className="la-stat-sub">{sub}</div>}
    </div>
  );
}

function ToggleField({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="la-toggle-field">
      <label>{label}</label>
      <button className={`la-toggle ${value ? 'on' : 'off'}`} onClick={() => onChange(!value)}>
        <span className="la-toggle-knob" />
      </button>
    </div>
  );
}

function ProfileField({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div className="la-profile-field">
      <label>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} />
    </div>
  );
}
