import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadResume, generateColdEmail } from '../api';
import { ResumeMatch, ResumeProfile, ColdEmailResponse } from '../types';

interface ResumeUploadProps {
  open: boolean;
  onClose: () => void;
  mode?: 'modal' | 'page';
}

export default function ResumeUpload({ open, onClose, mode = 'modal' }: ResumeUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [matches, setMatches] = useState<ResumeMatch[]>([]);
  const [profile, setProfile] = useState<ResumeProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resumeText, setResumeText] = useState('');
  const [coldEmail, setColdEmail] = useState<ColdEmailResponse | null>(null);
  const [generatingEmail, setGeneratingEmail] = useState(false);
  const [emailCopied, setEmailCopied] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file');
      return;
    }
    setUploading(true);
    setError(null);
    setMatches([]);
    setProfile(null);
    setColdEmail(null);
    try {
      const data = await uploadResume(file);
      if (data.error) {
        setError(data.error);
      } else {
        setMatches(data.matches);
        setProfile(data.profile);
        setResumeText(`Skills: ${data.profile.skills.join(', ')}. Level: ${data.profile.experience_level}. Roles: ${data.profile.role_preferences.join(', ')}`);
      }
    } catch (e: any) {
      setError(e.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleGenerateEmail = async (jobId: string) => {
    setGeneratingEmail(true);
    setSelectedJobId(jobId);
    setColdEmail(null);
    try {
      const data = await generateColdEmail(jobId, resumeText);
      setColdEmail(data);
    } catch (e: any) {
      setColdEmail({ email: 'Failed to generate email', founder_name: '', company_name: '', role_title: '', error: e.message });
    } finally {
      setGeneratingEmail(false);
    }
  };

  const handleCopyEmail = () => {
    if (coldEmail?.email) {
      navigator.clipboard.writeText(coldEmail.email);
      setEmailCopied(true);
      setTimeout(() => setEmailCopied(false), 2000);
    }
  };

  const handleClose = () => {
    setMatches([]);
    setProfile(null);
    setError(null);
    setColdEmail(null);
    setSelectedJobId(null);
    onClose();
  };

  if (!open) return null;

  // ── Shared Content ─────────────────────────────────────
  const content = (
    <>
      {/* Upload Area */}
      {!profile && !uploading && (
        <div
          className={`resume-drop-zone rounded-xl border-2 p-8 text-center cursor-pointer ${dragOver ? 'drag-over' : ''}`}
          style={{
            borderStyle: 'dashed',
            borderColor: dragOver ? 'var(--color-accent)' : 'var(--color-border)',
            backgroundColor: dragOver ? 'var(--color-surface)' : 'transparent',
            transition: 'all 0.2s ease',
          }}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
          <div className="text-5xl mb-4">📎</div>
          <p className="text-base font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
            Drop your resume PDF here
          </p>
          <p className="text-sm" style={{ color: 'var(--color-muted)' }}>
            or click to browse — max 10MB
          </p>
        </div>
      )}

      {/* Uploading State */}
      {uploading && (
        <div className="flex flex-col items-center justify-center py-8">
          <div className="resume-spinner mb-4" />
          <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
            Analyzing your resume...
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
            Extracting skills, matching jobs, and ranking results
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 rounded-lg mb-4" style={{ backgroundColor: '#dc26261a', border: '1px solid #dc2626' }}>
          <p className="text-sm" style={{ color: '#dc2626' }}>{error}</p>
        </div>
      )}

      {/* Profile Summary */}
      {profile && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--color-text)' }}>
              Your Profile
            </h3>
            <button
              onClick={() => { setProfile(null); setMatches([]); setColdEmail(null); }}
              className="text-xs px-3 py-1 rounded-lg cursor-pointer"
              style={{ color: 'var(--color-accent)', border: '1px solid var(--color-accent)' }}
            >
              Upload New
            </button>
          </div>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
            <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--color-surface)' }}>
              <p className="text-xs font-semibold mb-1" style={{ color: 'var(--color-muted)' }}>Experience Level</p>
              <p className="text-sm font-bold" style={{ color: 'var(--color-accent)' }}>{profile.experience_level}</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--color-surface)' }}>
              <p className="text-xs font-semibold mb-1" style={{ color: 'var(--color-muted)' }}>Best Fit Roles</p>
              <p className="text-sm font-bold" style={{ color: 'var(--color-accent)' }}>{profile.role_preferences.join(', ')}</p>
            </div>
            <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--color-surface)' }}>
              <p className="text-xs font-semibold mb-1" style={{ color: 'var(--color-muted)' }}>Skills Found</p>
              <p className="text-sm font-bold" style={{ color: 'var(--color-accent)' }}>{profile.skills.length}</p>
            </div>
          </div>
          {profile.skills.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {profile.skills.map((skill, i) => (
                <span key={i} className="badge" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-accent)' }}>
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Matched Jobs */}
      {matches.length > 0 && (
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--color-text)' }}>
            Top {matches.length} Matching Jobs
          </h3>
          <div className="space-y-3">
            {matches.map((match, i) => (
              <motion.div
                key={match.job.id || i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-4 rounded-xl border"
                style={{
                  backgroundColor: 'var(--color-card)',
                  borderColor: selectedJobId === match.job.id ? 'var(--color-accent)' : 'var(--color-border)',
                }}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-base font-bold" style={{ color: 'var(--color-text)' }}>
                        {match.job.company_name}
                      </h4>
                      <span
                        className="badge"
                        style={{
                          backgroundColor: match.match_score >= 50 ? '#059669' : match.match_score >= 30 ? '#d97706' : 'var(--color-surface)',
                          color: match.match_score >= 30 ? '#fff' : 'var(--color-muted)',
                        }}
                      >
                        {match.match_score}% match
                      </span>
                    </div>
                    <p className="text-sm" style={{ color: 'var(--color-accent)' }}>{match.job.role_title}</p>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {match.job.stage && (
                      <span className="badge border" style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}>
                        {match.job.stage}
                      </span>
                    )}
                  </div>
                </div>

                {/* Match reasons */}
                {match.reasons.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {match.reasons.map((reason, j) => (
                      <span key={j} className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-muted)' }}>
                        ✓ {reason}
                      </span>
                    ))}
                  </div>
                )}

                {/* Matched skills */}
                {match.matched_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {match.matched_skills.map((skill, j) => (
                      <span key={j} className="badge" style={{ backgroundColor: 'var(--color-accent)', color: '#fff', fontSize: '0.65rem' }}>
                        {skill}
                      </span>
                    ))}
                  </div>
                )}

                {/* Meta */}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
                  {match.job.salary_range && <span>💰 {match.job.salary_range}</span>}
                  {match.job.team_size && <span>👥 {match.job.team_size}</span>}
                  {(match.job.city || match.job.country) && <span>📍 {[match.job.city, match.job.country].filter(Boolean).join(', ')}</span>}
                  {match.job.work_type && <span className="capitalize">🏢 {match.job.work_type}</span>}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleGenerateEmail(match.job.id)}
                    disabled={generatingEmail && selectedJobId === match.job.id}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
                    style={{
                      backgroundColor: 'var(--color-accent)',
                      color: '#fff',
                      opacity: (generatingEmail && selectedJobId === match.job.id) ? 0.6 : 1,
                    }}
                  >
                    {generatingEmail && selectedJobId === match.job.id ? 'Generating...' : '✉️ Generate Cold Email'}
                  </button>
                  {match.job.job_url && (
                    <a
                      href={match.job.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 rounded-lg text-xs font-medium border"
                      style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)', textDecoration: 'none' }}
                    >
                      Apply →
                    </a>
                  )}
                </div>

                {/* Cold Email Result */}
                {coldEmail && selectedJobId === match.job.id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-3 p-4 rounded-lg"
                    style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-semibold" style={{ color: 'var(--color-accent)' }}>
                        Cold Email to {coldEmail.founder_name}
                      </p>
                      <button
                        onClick={handleCopyEmail}
                        className="text-xs px-2 py-1 rounded cursor-pointer"
                        style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}
                      >
                        {emailCopied ? '✓ Copied!' : '📋 Copy'}
                      </button>
                    </div>
                    {coldEmail.founder_linkedin && (
                      <a
                        href={coldEmail.founder_linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs mb-2 inline-block"
                        style={{ color: 'var(--color-accent)' }}
                      >
                        LinkedIn Profile →
                      </a>
                    )}
                    <pre className="text-sm whitespace-pre-wrap leading-relaxed mt-2" style={{ color: 'var(--color-text)', fontFamily: 'inherit' }}>
                      {coldEmail.email}
                    </pre>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </>
  );

  // ── Full Page Mode ─────────────────────────────────────
  if (mode === 'page') {
    return (
      <div className="resume-fullpage">
        <div className="resume-fullpage-inner">
          <div className="resume-fullpage-header">
            <div>
              <h2 className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
                📄 Resume Job Matcher
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-muted)' }}>
                Upload your resume to find matching jobs and generate personalized cold emails
              </p>
            </div>
            <button
              onClick={handleClose}
              className="agent-fullpage-back"
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-muted)',
                cursor: 'pointer',
                padding: '0.5rem 1rem',
                borderRadius: '0.5rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
              }}
            >
              ← Back to Dashboard
            </button>
          </div>
          {content}
        </div>
      </div>
    );
  }

  // ── Modal Mode (original) ──────────────────────────────
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
        onClick={handleClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.25 }}
          className="resume-modal rounded-xl border overflow-hidden"
          style={{
            backgroundColor: 'var(--color-bg)',
            borderColor: 'var(--color-border)',
            width: '90vw',
            maxWidth: '900px',
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-6 py-4 border-b"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <div>
              <h2 className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
                📄 Resume Job Matcher
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-muted)' }}>
                Upload your resume to find matching jobs and generate personalized cold emails
              </p>
            </div>
            <button
              onClick={handleClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer"
              style={{ color: 'var(--color-muted)' }}
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="overflow-y-auto" style={{ flex: 1, padding: '1.5rem' }}>
            {content}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
