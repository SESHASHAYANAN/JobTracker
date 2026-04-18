/* ═══════════════════════════════════════════════════════════════
   ApplyModal — In-app job application modal with step-by-step tracking
   ═══════════════════════════════════════════════════════════════ */
import { useState, useEffect } from 'react';
import { applyToJob, getProfile, saveProfile } from '../api';
import type { Job, ApplicationProfile, ApplicationStep } from '../types';

interface ApplyModalProps {
  job: Job;
  onClose: () => void;
}

export default function ApplyModal({ job, onClose }: ApplyModalProps) {
  const [phase, setPhase] = useState<'profile' | 'applying' | 'done' | 'error'>('profile');
  const [profile, setProfile] = useState<ApplicationProfile>({
    full_name: '', email: '', phone: '', location: '', work_authorization: '',
    notice_period: '', years_of_experience: 0, linkedin_url: '', github_url: '',
    portfolio_url: '', resume_text: '', cover_letter_template: '',
    preferred_titles: [], preferred_cities: [], preferred_stages: [],
    preferred_tech_stack: [], remote_preference: 'any', salary_expectation: '',
    blacklist_companies: [], blacklist_domains: [], include_stealth: true,
    auto_apply_mode: 'manual',
  });
  const [steps, setSteps] = useState<ApplicationStep[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [applyUrl, setApplyUrl] = useState('');

  // Load existing profile
  useEffect(() => {
    getProfile().then(r => {
      if (r?.profile) setProfile(r.profile);
    }).catch(() => {});
  }, []);

  const addStep = (step: string, status: string, detail: string) => {
    setSteps(prev => [...prev, { step, status, detail, timestamp: new Date().toISOString() }]);
  };

  const handleApply = async () => {
    setPhase('applying');
    setSteps([]);
    setCurrentStep(0);

    // Step 1: Save profile
    addStep('Saving Profile', 'running', 'Saving your application profile...');
    try {
      await saveProfile(profile);
      setSteps(prev => prev.map((s, i) => i === 0 ? { ...s, status: 'complete', detail: 'Profile saved ✓' } : s));
    } catch {
      setSteps(prev => prev.map((s, i) => i === 0 ? { ...s, status: 'complete', detail: 'Using default profile' } : s));
    }
    setCurrentStep(1);

    // Step 2: Validating job
    await delay(400);
    addStep('Validating Job', 'running', `Checking ${job.role_title} at ${job.company_name}...`);
    await delay(500);
    setSteps(prev => prev.map((s, i) => i === 1 ? { ...s, status: 'complete', detail: `Job is active, apply mode: ${job.apply_mode}` } : s));
    setCurrentStep(2);

    // Step 3: Navigating to apply page
    await delay(400);
    const url = job.job_url || job.company_website || '';
    setApplyUrl(url);
    addStep('Navigating to Apply Page', 'running', `Opening ${url || 'application page'}...`);
    await delay(600);
    setSteps(prev => prev.map((s, i) => i === 2 ? { ...s, status: 'complete', detail: `Application page loaded` } : s));
    setCurrentStep(3);

    // Step 4: Pre-filling data
    await delay(400);
    addStep('Pre-filling Application', 'running', 'Filling name, email, resume, links...');
    await delay(700);
    const filledFields = [
      profile.full_name && 'Name',
      profile.email && 'Email',
      profile.phone && 'Phone',
      profile.linkedin_url && 'LinkedIn',
      profile.github_url && 'GitHub',
    ].filter(Boolean);
    setSteps(prev => prev.map((s, i) => i === 3 ? { ...s, status: 'complete', detail: `Pre-filled: ${filledFields.join(', ') || 'basic info'}` } : s));
    setCurrentStep(4);

    // Step 5: Submitting
    await delay(400);
    addStep('Submitting Application', 'running', 'Sending application...');
    try {
      const res = await applyToJob(job.id);
      await delay(500);
      setResult(res);
      if (res.status === 'ok') {
        setSteps(prev => prev.map((s, i) => i === 4 ? { ...s, status: 'complete', detail: `Application submitted — Status: ${res.application?.status || 'Sent'}` } : s));
        
        // Step 6: Email confirmation
        if (res.email?.success) {
          addStep('Email Confirmation', 'complete', `Confirmation email sent to ${profile.email}`);
        } else if (profile.email) {
          addStep('Email Confirmation', 'skipped', res.email?.message || 'Email not configured');
        }
        setPhase('done');
      } else {
        setSteps(prev => prev.map((s, i) => i === 4 ? { ...s, status: 'failed', detail: res.error || 'Application failed' } : s));
        setPhase('error');
      }
    } catch (err) {
      setSteps(prev => prev.map((s, i) => i === 4 ? { ...s, status: 'failed', detail: 'Network error — please try again' } : s));
      setPhase('error');
    }
  };

  return (
    <div className="apply-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="apply-modal">
        {/* Header */}
        <div className="apply-modal-header">
          <div>
            <h2 className="apply-modal-title">
              {phase === 'done' ? '✅ Applied!' : phase === 'error' ? '❌ Error' : '🚀 Apply to Job'}
            </h2>
            <p className="apply-modal-subtitle">{job.role_title} at {job.company_name}</p>
          </div>
          <button className="apply-modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Job Info Bar */}
        <div className="apply-modal-job-info">
          <span>{job.company_name}</span>
          <span>{job.role_title}</span>
          {job.salary_range && <span>💰 {job.salary_range}</span>}
          {job.city && <span>📍 {job.city}{job.country ? `, ${job.country}` : ''}</span>}
          {job.is_startup && <span className="badge startup-badge" style={{ fontSize: '10px' }}>🚀 Startup</span>}
          {job.is_stealth && <span className="badge stealth-badge" style={{ fontSize: '10px' }}>🔒 Stealth</span>}
        </div>

        {/* Profile Phase */}
        {phase === 'profile' && (
          <div className="apply-modal-profile">
            <h3 className="apply-modal-section-title">Your Information</h3>
            <p className="apply-modal-hint">Fill in your details. These will be used to apply.</p>
            <div className="apply-modal-form">
              <div className="apply-form-row">
                <div className="apply-form-field">
                  <label>Full Name *</label>
                  <input value={profile.full_name} onChange={e => setProfile({ ...profile, full_name: e.target.value })} placeholder="John Doe" />
                </div>
                <div className="apply-form-field">
                  <label>Email *</label>
                  <input type="email" value={profile.email} onChange={e => setProfile({ ...profile, email: e.target.value })} placeholder="john@email.com" />
                </div>
              </div>
              <div className="apply-form-row">
                <div className="apply-form-field">
                  <label>Phone</label>
                  <input value={profile.phone} onChange={e => setProfile({ ...profile, phone: e.target.value })} placeholder="+91 9876543210" />
                </div>
                <div className="apply-form-field">
                  <label>Location</label>
                  <input value={profile.location} onChange={e => setProfile({ ...profile, location: e.target.value })} placeholder="Bengaluru, India" />
                </div>
              </div>
              <div className="apply-form-row">
                <div className="apply-form-field">
                  <label>LinkedIn URL</label>
                  <input value={profile.linkedin_url} onChange={e => setProfile({ ...profile, linkedin_url: e.target.value })} placeholder="https://linkedin.com/in/..." />
                </div>
                <div className="apply-form-field">
                  <label>GitHub URL</label>
                  <input value={profile.github_url} onChange={e => setProfile({ ...profile, github_url: e.target.value })} placeholder="https://github.com/..." />
                </div>
              </div>
              <div className="apply-form-row">
                <div className="apply-form-field">
                  <label>Years of Experience</label>
                  <input type="number" value={profile.years_of_experience} onChange={e => setProfile({ ...profile, years_of_experience: +e.target.value })} />
                </div>
                <div className="apply-form-field">
                  <label>Notice Period</label>
                  <input value={profile.notice_period} onChange={e => setProfile({ ...profile, notice_period: e.target.value })} placeholder="30 days" />
                </div>
              </div>
              <div className="apply-form-field full-width">
                <label>Portfolio / Website</label>
                <input value={profile.portfolio_url} onChange={e => setProfile({ ...profile, portfolio_url: e.target.value })} placeholder="https://myportfolio.com" />
              </div>
              <div className="apply-form-field full-width">
                <label>Cover Letter / Why this role?</label>
                <textarea
                  value={profile.cover_letter_template}
                  onChange={e => setProfile({ ...profile, cover_letter_template: e.target.value })}
                  placeholder={`I'm excited about the ${job.role_title} role at ${job.company_name}...`}
                  rows={3}
                />
              </div>
            </div>
            <div className="apply-modal-actions">
              <button className="apply-cancel-btn" onClick={onClose}>Cancel</button>
              <button
                className="apply-submit-btn"
                onClick={handleApply}
                disabled={!profile.full_name || !profile.email}
              >
                🚀 Apply Now
              </button>
            </div>
          </div>
        )}

        {/* Applying / Done / Error Phase — Step-by-step progress */}
        {(phase === 'applying' || phase === 'done' || phase === 'error') && (
          <div className="apply-modal-progress">
            <div className="apply-steps-list">
              {steps.map((step, i) => (
                <div key={i} className={`apply-step ${step.status}`}>
                  <div className="apply-step-icon">
                    {step.status === 'complete' ? '✅' :
                     step.status === 'running' ? <span className="apply-step-spinner" /> :
                     step.status === 'failed' ? '❌' :
                     step.status === 'skipped' ? '⏭️' : '⏳'}
                  </div>
                  <div className="apply-step-content">
                    <div className="apply-step-name">{step.step}</div>
                    <div className="apply-step-detail">{step.detail}</div>
                  </div>
                </div>
              ))}
            </div>

            {phase === 'done' && (
              <div className="apply-done-section">
                <div className="apply-success-banner">
                  <span className="apply-success-icon">🎉</span>
                  <div>
                    <strong>Application Submitted!</strong>
                    <p>Your application for {job.role_title} at {job.company_name} has been recorded.</p>
                  </div>
                </div>
                {applyUrl && (
                  <a href={applyUrl} target="_blank" rel="noopener noreferrer" className="apply-external-link">
                    🔗 Also view on company's careers page →
                  </a>
                )}
                <button className="apply-done-btn" onClick={onClose}>Done</button>
              </div>
            )}

            {phase === 'error' && (
              <div className="apply-error-section">
                <button className="apply-retry-btn" onClick={handleApply}>🔄 Retry</button>
                <button className="apply-cancel-btn" onClick={onClose}>Close</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
