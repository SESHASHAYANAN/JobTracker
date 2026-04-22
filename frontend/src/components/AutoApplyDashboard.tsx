/* ═══════════════════════════════════════════════════════════════
   AutoApplyDashboard — Full-page auto-apply management dashboard
   ═══════════════════════════════════════════════════════════════ */
import { useState, useEffect, useCallback } from 'react';
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

export default function AutoApplyDashboard() {
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
  const [activeTab, setActiveTab] = useState<'overview' | 'applications' | 'config' | 'profile'>('overview');
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedApp, setExpandedApp] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

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

  const handleRun = async () => {
    setIsRunning(true);
    setRunResult('');
    try {
      const r = await runAutoApply();
      setRunResult(`✅ Matched ${r.matched || 0} jobs — ${r.applied || 0} applied, ${r.needs_review || 0} need review`);
      load();
    } catch (e) {
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

  return (
    <div className="autoapply-dashboard">
      {/* Header */}
      <div className="aad-header">
        <div className="aad-header-left">
          <h1 className="aad-title">🚀 Auto-Apply Dashboard</h1>
          <p className="aad-subtitle">Startup Job Discovery & Application Assistant</p>
        </div>
        <div className="aad-header-actions">
          <button className={`aad-run-btn ${isRunning ? 'running' : ''}`} onClick={handleRun} disabled={isRunning}>
            {isRunning ? '⏳ Running...' : '▶ Run Auto-Apply'}
          </button>
        </div>
      </div>
      {runResult && <div className="aad-run-result">{runResult}</div>}

      {/* Tabs */}
      <div className="aad-tabs">
        {(['overview', 'applications', 'config', 'profile'] as const).map(tab => (
          <button key={tab} className={`aad-tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
            {tab === 'overview' ? '📊 Overview' : tab === 'applications' ? '📋 Applications' : tab === 'config' ? '⚙️ Config' : '👤 Profile'}
          </button>
        ))}
      </div>

      {/* ── Overview ── */}
      {activeTab === 'overview' && stats && (
        <div className="aad-overview">
          <div className="aad-stats-grid">
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
          <div className="aad-section">
            <h3 className="aad-section-title">🏷️ Top Startup Tech Stacks</h3>
            <div className="aad-tags-cloud">
              {stats.top_tech_stacks.map((t, i) => (
                <span key={i} className="aad-tech-tag" style={{ opacity: 0.6 + (t.count / (stats.top_tech_stacks[0]?.count || 1)) * 0.4 }}>
                  {t.name} <span className="aad-tag-count">{t.count}</span>
                </span>
              ))}
            </div>
          </div>
          {/* Top Domains */}
          <div className="aad-section">
            <h3 className="aad-section-title">🏢 Top Startup Domains</h3>
            <div className="aad-domain-bars">
              {stats.top_startup_domains.slice(0, 8).map((d, i) => (
                <div key={i} className="aad-domain-row">
                  <span className="aad-domain-name">{d.name}</span>
                  <div className="aad-domain-bar-bg">
                    <div className="aad-domain-bar-fill" style={{ width: `${(d.count / (stats.top_startup_domains[0]?.count || 1)) * 100}%` }} />
                  </div>
                  <span className="aad-domain-count">{d.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Applications ── */}
      {activeTab === 'applications' && (
        <div className="aad-applications">
          <div className="aad-app-filters">
            {['', 'Applied', 'Pending', 'Needs Review', 'Failed', 'Skipped'].map(s => (
              <button key={s} className={`aad-filter-btn ${statusFilter === s ? 'active' : ''}`} onClick={() => setStatusFilter(s)}>
                {s || 'All'} {s ? `(${applications.filter(a => a.status === s).length})` : `(${applications.length})`}
              </button>
            ))}
          </div>
          {filteredApps.length === 0 ? (
            <div className="aad-empty">No applications yet. Run Auto-Apply or apply to jobs from the job board.</div>
          ) : (
            <div className="aad-app-list">
              {filteredApps.map(app => (
                <div key={app.id} className={`aad-app-card ${app.status.toLowerCase().replace(' ', '-')}`}>
                  <div className="aad-app-main" onClick={() => setExpandedApp(expandedApp === app.id ? null : app.id)}>
                    <div className="aad-app-info">
                      <h4 className="aad-app-role">{app.role_title}</h4>
                      <p className="aad-app-company">{app.company_name}</p>
                    </div>
                    <div className="aad-app-meta">
                      <span className={`aad-app-status ${app.status.toLowerCase().replace(' ', '-')}`}>{app.status}</span>
                      <span className="aad-app-method">{app.method === 'auto' ? '🤖' : app.method === 'one_click' ? '⚡' : '🔗'} {app.method}</span>
                      <span className="aad-app-time">{timeAgo(app.applied_at)}</span>
                      {app.email_sent && <span className="aad-app-email-badge">📧</span>}
                    </div>
                  </div>
                  {expandedApp === app.id && (
                    <div className="aad-app-details">
                      <div className="aad-app-steps">
                        {app.steps.map((step, i) => (
                          <div key={i} className={`aad-step ${step.status}`}>
                            <span className="aad-step-icon">
                              {step.status === 'complete' ? '✅' : step.status === 'pending' ? '⏳' : '⏭️'}
                            </span>
                            <div className="aad-step-content">
                              <strong>{step.step}</strong>
                              <p>{step.detail}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                      {app.apply_url && (
                        <a href={app.apply_url} target="_blank" rel="noopener noreferrer" className="aad-open-link">🔗 Open Application Page</a>
                      )}
                      <div className="aad-app-actions">
                        {app.status === 'Needs Review' && (
                          <button className="aad-approve-btn" onClick={() => handleStatusUpdate(app.id, 'Applied')}>✅ Approve & Apply</button>
                        )}
                        {app.status !== 'Skipped' && app.status !== 'Applied' && (
                          <button className="aad-skip-btn" onClick={() => handleStatusUpdate(app.id, 'Skipped')}>⏭️ Skip</button>
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

      {/* ── Config ── */}
      {activeTab === 'config' && (
        <div className="aad-config">
          <h3 className="aad-section-title">⚙️ Auto-Apply Configuration</h3>
          <div className="aad-config-grid">
            <ToggleField label="Enable Auto-Apply" value={config.enabled} onChange={v => setConfig({ ...config, enabled: v })} />
            <ToggleField label="Startup Jobs Only" value={config.startup_only} onChange={v => setConfig({ ...config, startup_only: v })} />
            <ToggleField label="India Only" value={config.india_only} onChange={v => setConfig({ ...config, india_only: v })} />
            <ToggleField label="Remote India" value={config.remote_india} onChange={v => setConfig({ ...config, remote_india: v })} />
            <ToggleField label="Engineering Only" value={config.engineering_only} onChange={v => setConfig({ ...config, engineering_only: v })} />
            <ToggleField label="Paused" value={config.paused} onChange={v => setConfig({ ...config, paused: v })} />
            <div className="aad-config-field">
              <label>Min Match Score</label>
              <input type="range" min={0} max={100} value={config.min_match_score} onChange={e => setConfig({ ...config, min_match_score: +e.target.value })} />
              <span className="aad-range-value">{config.min_match_score}%</span>
            </div>
            <div className="aad-config-field">
              <label>Max Daily Applications</label>
              <input type="number" min={1} max={50} value={config.max_daily_applications} onChange={e => setConfig({ ...config, max_daily_applications: +e.target.value })} />
            </div>
            <div className="aad-config-field">
              <label>Max Days Old</label>
              <input type="number" min={1} max={90} value={config.max_days_old} onChange={e => setConfig({ ...config, max_days_old: +e.target.value })} />
            </div>
            <div className="aad-config-field">
              <label>Approval Mode</label>
              <select value={config.approval_mode} onChange={e => setConfig({ ...config, approval_mode: e.target.value })}>
                <option value="approval">Approval Required</option>
                <option value="one_click">One-Click</option>
                <option value="batch">Batch Approval</option>
                <option value="automatic">Fully Automatic</option>
              </select>
            </div>
          </div>
          <button className="aad-save-btn" onClick={handleSaveConfig} disabled={saving}>
            {saving ? 'Saving...' : '💾 Save Configuration'}
          </button>
        </div>
      )}

      {/* ── Profile ── */}
      {activeTab === 'profile' && (
        <div className="aad-profile">
          <h3 className="aad-section-title">👤 Application Profile</h3>
          <p className="aad-profile-hint">This information is used to pre-fill applications and send confirmation emails.</p>
          <div className="aad-profile-grid">
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
            <div className="aad-profile-field full-width">
              <label>Preferred Cities (comma-separated)</label>
              <input value={profile.preferred_cities.join(', ')} onChange={e => setProfile({ ...profile, preferred_cities: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
            <div className="aad-profile-field full-width">
              <label>Preferred Tech Stack (comma-separated)</label>
              <input value={profile.preferred_tech_stack.join(', ')} onChange={e => setProfile({ ...profile, preferred_tech_stack: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
            <div className="aad-profile-field full-width">
              <label>Blacklist Companies (comma-separated)</label>
              <input value={profile.blacklist_companies.join(', ')} onChange={e => setProfile({ ...profile, blacklist_companies: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
            </div>
          </div>
          <button className="aad-save-btn" onClick={handleSaveProfile} disabled={saving}>
            {saving ? 'Saving...' : '💾 Save Profile'}
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ── */

function StatCard({ icon, label, value, sub, color }: { icon: string; label: string; value: number; sub?: string; color: string }) {
  return (
    <div className="aad-stat-card" style={{ borderTop: `3px solid ${color}` }}>
      <span className="aad-stat-icon">{icon}</span>
      <div className="aad-stat-value">{value.toLocaleString()}</div>
      <div className="aad-stat-label">{label}</div>
      {sub && <div className="aad-stat-sub">{sub}</div>}
    </div>
  );
}

function ToggleField({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="aad-toggle-field">
      <label>{label}</label>
      <button className={`aad-toggle ${value ? 'on' : 'off'}`} onClick={() => onChange(!value)}>
        <span className="aad-toggle-knob" />
      </button>
    </div>
  );
}

function ProfileField({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div className="aad-profile-field">
      <label>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} />
    </div>
  );
}
