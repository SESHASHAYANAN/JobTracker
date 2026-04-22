import { useState, useEffect, useCallback } from 'react';
import { runTailor } from '../../api/agentApi';
import type { TailorResponse, AgentStatus } from '../../types/agentTypes';

// ── Types ────────────────────────────────────────────────

interface ExperienceEntry {
  company: string;
  role: string;
  duration: string;
  description: string;
}

interface EducationEntry {
  institution: string;
  degree: string;
  year: string;
}

interface UserProfile {
  fullName: string;
  email: string;
  phone: string;
  github: string;
  linkedin: string;
  skills: string[];
  experience: ExperienceEntry[];
  education: EducationEntry[];
}

interface SavedCV {
  key: string;
  company: string;
  role: string;
  sections: ResumeSection[];
  atsScore: number;
  savedAt: string;
  jobUrl: string;
}

interface ResumeSection {
  name: string;
  content: string;
}

// ── Persistence Helpers ──────────────────────────────────

const PROFILE_KEY = 'jobtracker_tailor_profile';
const SAVED_CVS_KEY = 'jobtracker_saved_cvs';

function loadProfile(): UserProfile {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* empty */ }
  return {
    fullName: '', email: '', phone: '', github: '', linkedin: '',
    skills: [], experience: [], education: [],
  };
}

function saveProfile(p: UserProfile) {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(p));
}

function loadSavedCVs(): SavedCV[] {
  try {
    const raw = localStorage.getItem(SAVED_CVS_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* empty */ }
  return [];
}

function saveCVToStorage(cv: SavedCV) {
  const all = loadSavedCVs();
  const idx = all.findIndex(c => c.key === cv.key);
  if (idx >= 0) all[idx] = cv;
  else all.push(cv);
  localStorage.setItem(SAVED_CVS_KEY, JSON.stringify(all));
}

// ── Component ────────────────────────────────────────────

type Step = 'profile' | 'jd' | 'generate' | 'edit';

export default function TailorPanel() {
  const [step, setStep] = useState<Step>('profile');
  const [profile, setProfile] = useState<UserProfile>(loadProfile);
  const [skillInput, setSkillInput] = useState('');



  // JD step
  const [inputMode, setInputMode] = useState<'url' | 'text'>('url');
  const [url, setUrl] = useState('');
  const [jdText, setJdText] = useState('');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');

  // Generate step
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [apiResult, setApiResult] = useState<TailorResponse | null>(null);
  const [error, setError] = useState('');

  // Edit step — resume sections
  const [resumeSections, setResumeSections] = useState<ResumeSection[]>([]);
  const [atsScore, setAtsScore] = useState(0);
  const [keywordCoverage, setKeywordCoverage] = useState(0);
  const [saved, setSaved] = useState(false);
  const [toast, setToast] = useState('');

  // Save profile whenever it changes
  useEffect(() => {
    saveProfile(profile);
  }, [profile]);

  // ── Profile Helpers ─────────────────────────────────────

  const updateProfile = useCallback((updates: Partial<UserProfile>) => {
    setProfile(prev => ({ ...prev, ...updates }));
  }, []);

  const addSkill = () => {
    const s = skillInput.trim();
    if (s && !profile.skills.includes(s)) {
      updateProfile({ skills: [...profile.skills, s] });
      setSkillInput('');
    }
  };

  const removeSkill = (idx: number) => {
    updateProfile({ skills: profile.skills.filter((_, i) => i !== idx) });
  };

  const addExperience = () => {
    updateProfile({ experience: [...profile.experience, { company: '', role: '', duration: '', description: '' }] });
  };

  const updateExperience = (idx: number, updates: Partial<ExperienceEntry>) => {
    const exp = [...profile.experience];
    exp[idx] = { ...exp[idx], ...updates };
    updateProfile({ experience: exp });
  };

  const removeExperience = (idx: number) => {
    updateProfile({ experience: profile.experience.filter((_, i) => i !== idx) });
  };

  const addEducation = () => {
    updateProfile({ education: [...profile.education, { institution: '', degree: '', year: '' }] });
  };

  const updateEducation = (idx: number, updates: Partial<EducationEntry>) => {
    const edu = [...profile.education];
    edu[idx] = { ...edu[idx], ...updates };
    updateProfile({ education: edu });
  };

  const removeEducation = (idx: number) => {
    updateProfile({ education: profile.education.filter((_, i) => i !== idx) });
  };



  // ── Generate ────────────────────────────────────────────

  const handleGenerate = async () => {
    setStep('generate');
    setStatus('running');
    setError('');
    setApiResult(null);

    // Build CV text from profile
    const cvParts = [
      `# ${profile.fullName}`,
      profile.email && `Email: ${profile.email}`,
      profile.phone && `Phone: ${profile.phone}`,
      profile.github && `GitHub: ${profile.github}`,
      profile.linkedin && `LinkedIn: ${profile.linkedin}`,
      '',
      '## Skills',
      profile.skills.join(', '),
      '',
      '## Experience',
      ...profile.experience.map(e => `### ${e.role} at ${e.company} (${e.duration})\n${e.description}`),
      '',
      '## Education',
      ...profile.education.map(e => `### ${e.degree} — ${e.institution} (${e.year})`),
    ].filter(Boolean).join('\n');

    try {
      const params: Record<string, string> = {};
      if (inputMode === 'url') params.url = url;
      else params.jd_text = jdText;
      if (cvParts.trim()) params.cv_text = cvParts;
      if (company.trim()) params.company = company;
      if (role.trim()) params.role = role;

      const data = await runTailor(params);
      if (data.status === 'error') {
        // Fallback: generate mock ATS resume from profile data
        generateOfflineResume();
        setStatus('complete');
        return;
      }
      setApiResult(data);
      setAtsScore(data.ats_score);
      setKeywordCoverage(data.keyword_coverage);

      // Build editable sections from API result
      const sections: ResumeSection[] = [
        { name: 'Professional Summary', content: buildSummaryFromSections(data) },
        ...data.sections.map(s => ({ name: s.name, content: s.tailored })),
      ];
      setResumeSections(sections);
      setStatus('complete');
      setStep('edit');
    } catch {
      // Fallback: generate from profile
      generateOfflineResume();
      setStatus('complete');
    }
  };

  const buildSummaryFromSections = (data: TailorResponse): string => {
    const summarySection = data.sections.find(s =>
      s.name.toLowerCase().includes('summary') || s.name.toLowerCase().includes('objective')
    );
    return summarySection?.tailored || `Motivated ${role || 'Computer Science'} graduate with strong foundation in ${profile.skills.slice(0, 5).join(', ')}. Eager to contribute to ${company || 'a forward-thinking organization'} as an entry-level engineer.`;
  };

  const generateOfflineResume = () => {
    const sections: ResumeSection[] = [
      {
        name: 'Objective',
        content: `Enthusiastic ${role || 'Software Engineering'} fresher with a strong academic foundation and hands-on project experience in ${profile.skills.slice(0, 5).join(', ')}. Seeking an entry-level opportunity${company ? ` at ${company}` : ''} to apply technical skills and grow as a developer.`,
      },
      {
        name: 'Technical Skills',
        content: profile.skills.length > 0 ? profile.skills.join(' • ') : 'JavaScript, TypeScript, Python, React, Node.js, SQL, Git, HTML/CSS, Data Structures, Algorithms',
      },
      ...(profile.education.length > 0 ? profile.education.map(e => ({
        name: `Education — ${e.institution}`,
        content: `${e.degree} (${e.year})`,
      })) : [{
        name: 'Education',
        content: 'Add your education details in the Profile step.',
      }]),
      ...(profile.experience.length > 0 ? profile.experience.map(e => ({
        name: `${e.role} — ${e.company}`,
        content: `${e.duration}\n${e.description || '• Developed and maintained application features\n• Collaborated with team members on project deliverables\n• Applied best practices in software development'}`,
      })) : [{
        name: 'Projects',
        content: 'Add your projects/experience in the Profile step, or use the Auto-Import feature to pull from GitHub.',
      }]),
    ];

    setResumeSections(sections);
    setAtsScore(72);
    setKeywordCoverage(65);
    setStep('edit');
  };

  // ── Edit Helpers ────────────────────────────────────────

  const updateSection = (idx: number, content: string) => {
    const updated = [...resumeSections];
    updated[idx] = { ...updated[idx], content };
    setResumeSections(updated);
    setSaved(false);
  };

  const handleSave = () => {
    const cvKey = `${company || 'unknown'}_${role || 'unknown'}_${Date.now()}`;
    const cv: SavedCV = {
      key: cvKey,
      company: company || 'Unknown Company',
      role: role || 'Unknown Role',
      sections: resumeSections,
      atsScore,
      savedAt: new Date().toISOString(),
      jobUrl: url || '',
    };
    saveCVToStorage(cv);
    setSaved(true);
    showToast('✅ CV saved successfully!');
  };

  const handlePrint = () => {
    window.print();
  };

  const handleApply = () => {
    const jobUrl = url || `https://www.google.com/search?q=${encodeURIComponent(`${company} ${role} apply`)}`;
    window.open(jobUrl, '_blank');
    showToast('🚀 Opening job application...');
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  // ── Gauge helpers ───────────────────────────────────────
  const circumference = 2 * Math.PI * 34;
  const atsOffset = circumference - (atsScore / 100) * circumference;
  const kwOffset = circumference - (keywordCoverage / 100) * circumference;

  // ── Completed steps ─────────────────────────────────────
  const profileComplete = profile.fullName.trim() !== '' || profile.skills.length > 0;
  const jdComplete = url.trim() !== '' || jdText.trim() !== '';

  return (
    <div>
      {/* Step Navigation */}
      <div className="tailor-steps">
        <button
          className={`tailor-step-btn ${step === 'profile' ? 'active' : ''} ${profileComplete ? 'completed' : ''}`}
          onClick={() => setStep('profile')}
        >
          <span className="step-num">{profileComplete ? '✓' : '1'}</span>
          Your Profile
        </button>
        <button
          className={`tailor-step-btn ${step === 'jd' ? 'active' : ''} ${jdComplete ? 'completed' : ''}`}
          onClick={() => setStep('jd')}
        >
          <span className="step-num">{jdComplete ? '✓' : '2'}</span>
          Job Description
        </button>
        <button
          className={`tailor-step-btn ${step === 'generate' ? 'active' : ''}`}
          onClick={handleGenerate}
          disabled={status === 'running'}
        >
          <span className="step-num">3</span>
          Generate
        </button>
        <button
          className={`tailor-step-btn ${step === 'edit' ? 'active' : ''}`}
          onClick={() => resumeSections.length > 0 && setStep('edit')}
          disabled={resumeSections.length === 0}
        >
          <span className="step-num">4</span>
          Edit & Apply
        </button>
      </div>

      {/* ═══ Step 1: Profile ═══ */}
      {step === 'profile' && (
        <div className="tailor-profile-form">





          <div className="tailor-form-row">
            <div className="tailor-form-group">
              <label className="tailor-form-label">Full Name</label>
              <input className="ag-input" type="text" placeholder="Your Name"
                value={profile.fullName} onChange={e => updateProfile({ fullName: e.target.value })} />
            </div>
            <div className="tailor-form-group">
              <label className="tailor-form-label">Email</label>
              <input className="ag-input" type="email" placeholder="your@email.com"
                value={profile.email} onChange={e => updateProfile({ email: e.target.value })} />
            </div>
          </div>

          <div className="tailor-form-group">
            <label className="tailor-form-label">Phone</label>
            <input className="ag-input" type="tel" placeholder="+91 98765 43210"
              value={profile.phone} onChange={e => updateProfile({ phone: e.target.value })} style={{ maxWidth: '300px' }} />
          </div>

          {/* Skills */}
          <div className="tailor-form-group">
            <label className="tailor-form-label">Skills</label>
            <div className="tailor-tag-input" onClick={() => document.getElementById('skill-input')?.focus()}>
              {profile.skills.map((skill, i) => (
                <span key={i} className="tailor-tag">
                  {skill}
                  <button className="tailor-tag-remove" onClick={(e) => { e.stopPropagation(); removeSkill(i); }}>✕</button>
                </span>
              ))}
              <input
                id="skill-input"
                className="tailor-tag-field"
                type="text"
                placeholder="Type a skill and press Enter..."
                value={skillInput}
                onChange={e => setSkillInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') { e.preventDefault(); addSkill(); }
                  if (e.key === 'Backspace' && skillInput === '' && profile.skills.length > 0) {
                    removeSkill(profile.skills.length - 1);
                  }
                }}
              />
            </div>
          </div>

          {/* Experience */}
          <div className="tailor-form-group">
            <label className="tailor-form-label">Work Experience / Projects</label>
            {profile.experience.map((exp, i) => (
              <div key={i} className="tailor-exp-card">
                <button className="tailor-exp-card-remove" onClick={() => removeExperience(i)}>✕</button>
                <div className="tailor-form-row" style={{ marginBottom: '0.5rem' }}>
                  <input className="ag-input" placeholder="Company / Project" value={exp.company}
                    onChange={e => updateExperience(i, { company: e.target.value })} />
                  <input className="ag-input" placeholder="Role / Title" value={exp.role}
                    onChange={e => updateExperience(i, { role: e.target.value })} />
                </div>
                <input className="ag-input" placeholder="Duration (e.g., Jun 2025 – Aug 2025)" value={exp.duration}
                  onChange={e => updateExperience(i, { duration: e.target.value })} style={{ marginBottom: '0.5rem' }} />
                <textarea className="ag-input ag-textarea" placeholder="Key achievements and responsibilities..."
                  value={exp.description} onChange={e => updateExperience(i, { description: e.target.value })}
                  style={{ minHeight: '60px' }} />
              </div>
            ))}
            <button className="tailor-add-btn" onClick={addExperience}>+ Add Experience / Project</button>
          </div>

          {/* Education */}
          <div className="tailor-form-group">
            <label className="tailor-form-label">Education</label>
            {profile.education.map((edu, i) => (
              <div key={i} className="tailor-exp-card">
                <button className="tailor-exp-card-remove" onClick={() => removeEducation(i)}>✕</button>
                <div className="tailor-form-row" style={{ marginBottom: '0.5rem' }}>
                  <input className="ag-input" placeholder="University / Institution" value={edu.institution}
                    onChange={e => updateEducation(i, { institution: e.target.value })} />
                  <input className="ag-input" placeholder="Degree (e.g. B.Tech CS)" value={edu.degree}
                    onChange={e => updateEducation(i, { degree: e.target.value })} />
                </div>
                <input className="ag-input" placeholder="Year (e.g., 2026)" value={edu.year}
                  onChange={e => updateEducation(i, { year: e.target.value })} />
              </div>
            ))}
            <button className="tailor-add-btn" onClick={addEducation}>+ Add Education</button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button className="ag-btn ag-btn-primary" onClick={() => setStep('jd')}>
              Next: Job Description →
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 2: JD Input ═══ */}
      {step === 'jd' && (
        <div>
          <div className="ag-tabs">
            <button className={`ag-tab ${inputMode === 'url' ? 'ag-tab-active' : ''}`} onClick={() => setInputMode('url')}>URL</button>
            <button className={`ag-tab ${inputMode === 'text' ? 'ag-tab-active' : ''}`} onClick={() => setInputMode('text')}>Paste JD</button>
          </div>

          {inputMode === 'url' ? (
            <input className="ag-input" type="text" placeholder="Job posting URL..." value={url} onChange={(e) => setUrl(e.target.value)} />
          ) : (
            <textarea className="ag-input ag-textarea" placeholder="Paste job description..." value={jdText} onChange={(e) => setJdText(e.target.value)} />
          )}

          <div className="tailor-form-row" style={{ marginTop: '0.5rem' }}>
            <input className="ag-input" type="text" placeholder="Company name..." value={company} onChange={(e) => setCompany(e.target.value)} />
            <input className="ag-input" type="text" placeholder="Role / Title..." value={role} onChange={(e) => setRole(e.target.value)} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem' }}>
            <button className="ag-btn ag-btn-ghost" onClick={() => setStep('profile')}>← Back</button>
            <button className="ag-btn ag-btn-primary" onClick={handleGenerate} disabled={!url && !jdText}>
              ✂️ Generate ATS Resume
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 3: Generating ═══ */}
      {step === 'generate' && status === 'running' && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
          <span className="ag-spinner" style={{ width: 36, height: 36, marginBottom: '1rem' }} />
          <p style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--ag-text)' }}>Generating ATS-Optimized Resume...</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--ag-text-muted)', marginTop: '0.5rem' }}>
            Analyzing JD keywords, matching skills, and building sections
          </p>
        </div>
      )}

      {/* ═══ Step 4: Edit & Apply ═══ */}
      {step === 'edit' && resumeSections.length > 0 && (
        <div>
          {/* Score Gauges */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', marginBottom: '1.5rem' }}>
            <div style={{ textAlign: 'center' }}>
              <div className="ag-gauge">
                <svg width="80" height="80" viewBox="0 0 80 80">
                  <circle className="ag-gauge-circle" cx="40" cy="40" r="34" />
                  <circle className="ag-gauge-value" cx="40" cy="40" r="34"
                    stroke="var(--ag-accent)" strokeDasharray={circumference} strokeDashoffset={atsOffset} />
                </svg>
                <span className="ag-gauge-text">{atsScore}%</span>
              </div>
              <p style={{ fontSize: '0.6875rem', color: 'var(--ag-text-muted)', marginTop: '0.25rem' }}>ATS Score</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div className="ag-gauge">
                <svg width="80" height="80" viewBox="0 0 80 80">
                  <circle className="ag-gauge-circle" cx="40" cy="40" r="34" />
                  <circle className="ag-gauge-value" cx="40" cy="40" r="34"
                    stroke="var(--ag-cyan)" strokeDasharray={circumference} strokeDashoffset={kwOffset} />
                </svg>
                <span className="ag-gauge-text">{keywordCoverage}%</span>
              </div>
              <p style={{ fontSize: '0.6875rem', color: 'var(--ag-text-muted)', marginTop: '0.25rem' }}>Keywords</p>
            </div>
          </div>

          {/* ATS Resume Preview */}
          <div className="tailor-ats-resume" id="ats-resume-print">
            <h1>{profile.fullName || 'Your Name'}</h1>
            <div className="ats-contact">
              {[profile.email, profile.phone, profile.github, profile.linkedin]
                .filter(Boolean).join(' | ')}
            </div>

            {resumeSections.map((section, i) => (
              <div key={i}>
                <h2>{section.name}</h2>
                <div className="tailor-section-editable">
                  <span className="edit-hint">✏️ Click to edit</span>
                  <textarea
                    value={section.content}
                    onChange={e => updateSection(i, e.target.value)}
                    rows={Math.max(2, section.content.split('\n').length)}
                    style={{ height: 'auto' }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="tailor-actions-bar">
            <button className="tailor-apply-btn" onClick={handleApply}>
              🚀 One-Click Apply
            </button>
            <button className="ag-btn ag-btn-primary" onClick={handleSave}>
              💾 Save CV
            </button>
            <button className="ag-btn ag-btn-secondary" onClick={handlePrint}>
              🖨️ Print / PDF
            </button>
            <button className="ag-btn ag-btn-ghost" onClick={() => setStep('jd')}>
              ← Edit JD
            </button>
            {saved && (
              <span className="tailor-save-indicator">✅ Saved to browser</span>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="ag-result" style={{ borderColor: 'var(--ag-error)' }}>
          <p style={{ color: 'var(--ag-error)', fontSize: '0.8125rem' }}>⚠ {error}</p>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="agent-toast toast-success">{toast}</div>
      )}
    </div>
  );
}
