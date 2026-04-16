import { useState } from 'react';
import { motion } from 'framer-motion';
import { Job, Founder } from '../types';
import { generateColdDM } from '../api';

interface JobCardProps {
  job: Job;
  index: number;
}

/* ── Helpers ───────────────────────────────────────────── */

/** Detect role domain from title + category for the spec box */
function detectRoleDomains(title: string, category?: string | null): string[] {
  const blob = `${title} ${category || ''}`.toLowerCase();
  const domains: string[] = [];

  if (/\bfront[-\s]?end\b|react|angular|vue|ui\b|ux\b|css|web dev/i.test(blob)) domains.push('Frontend');
  if (/\bback[-\s]?end\b|server|api|node|django|flask|rails|spring|go\b|rust\b/i.test(blob)) domains.push('Backend');
  if (/\bfull[-\s]?stack\b/i.test(blob)) domains.push('Full-Stack');
  if (/\b(machine learning|ml\b|deep learning|nlp|computer vision|ai\b|artificial intelligence|generative)/i.test(blob)) domains.push('ML / AI');
  if (/\bdata\b.*\b(engineer|scientist|analy)/i.test(blob) || /\bdata science\b/i.test(blob)) domains.push('Data');
  if (/\bdevops\b|sre\b|infra|platform|cloud|kubernetes|docker/i.test(blob)) domains.push('DevOps / Infra');
  if (/\bmobile\b|android|ios|flutter|react native|swift|kotlin/i.test(blob)) domains.push('Mobile');
  if (/\bsecurity\b|cyber|pentest|appsec/i.test(blob)) domains.push('Security');
  if (/\bdesign\b|product design|graphic/i.test(blob)) domains.push('Design');
  if (/\bproduct\b.*\bmanag/i.test(blob) || /\bpm\b/i.test(blob)) domains.push('Product');
  if (/\bqa\b|quality|test|sdet/i.test(blob)) domains.push('QA / Testing');
  if (/\bblockchain\b|web3|smart contract|solidity/i.test(blob)) domains.push('Blockchain');

  if (domains.length === 0) {
    if (/engineer|developer|software/i.test(blob)) domains.push('Software Engineering');
    else domains.push('General');
  }
  return domains;
}

/** Map experience_level to a user-friendly label */
function formatExperience(level?: string | null): string {
  if (!level) return 'Not specified';
  const l = level.toLowerCase();
  if (l.includes('intern') || l.includes('fresher')) return 'Intern / Fresher';
  if (l.includes('new grad') || l.includes('entry') || l.includes('junior')) return '0-2 yrs (Entry)';
  if (l.includes('mid')) return '2-5 yrs (Mid)';
  if (l.includes('senior')) return '5-8 yrs (Senior)';
  if (l.includes('staff')) return '8-12 yrs (Staff)';
  if (l.includes('principal') || l.includes('lead') || l.includes('director') || l.includes('head') || l.includes('vp')) return '10+ yrs (Lead+)';
  return level;
}

/** Check if a founder entry is a real person vs placeholder junk */
function isRealFounder(f: Founder): boolean {
  const nameLower = (f.name || '').toLowerCase().trim();
  const titleLower = (f.title || '').toLowerCase().trim();

  // Skip empty names
  if (!nameLower || nameLower.length < 2) return false;

  // Known placeholder patterns
  const placeholderNames = [
    'who we are', 'make something', 'our motto', 'our mission',
    'our vision', 'team member', 'unknown', 'n/a', 'the team',
    'company', 'about us', 'join us', 'open role', 'components',
    'ai', 'hiring', 'careers', 'people want', 'we are',
  ];
  if (placeholderNames.some(p => nameLower === p || nameLower.includes(p))) return false;

  // Skip very short single-word entries (e.g. "AI", "QA") — real names are 2+ words
  const words = nameLower.split(/\s+/).filter(w => w.length > 0);
  if (words.length < 2) return false;

  // If title is "Team Member" and the name doesn't look like a real 2+ word name, skip
  if (titleLower === 'team member') {
    // Real names typically start with a capital letter
    if (!/^[A-Z]/.test(f.name.trim())) return false;
  }

  return true;
}

/* ── Domain color palette ──────────────────────────────── */
const domainColors: Record<string, { bg: string; text: string }> = {
  'Frontend':            { bg: '#1e3a5f', text: '#7dd3fc' },
  'Backend':             { bg: '#1a3328', text: '#6ee7b7' },
  'Full-Stack':          { bg: '#312e81', text: '#c4b5fd' },
  'ML / AI':             { bg: '#4a1d6a', text: '#e9d5ff' },
  'Data':                { bg: '#3b1f1f', text: '#fca5a5' },
  'DevOps / Infra':      { bg: '#1f2937', text: '#93c5fd' },
  'Mobile':              { bg: '#422006', text: '#fdba74' },
  'Security':            { bg: '#1c1917', text: '#fbbf24' },
  'Design':              { bg: '#831843', text: '#f9a8d4' },
  'Product':             { bg: '#164e63', text: '#67e8f9' },
  'QA / Testing':        { bg: '#1e293b', text: '#94a3b8' },
  'Blockchain':          { bg: '#1a1a2e', text: '#a78bfa' },
  'Software Engineering':{ bg: '#1e293b', text: '#60a5fa' },
  'General':             { bg: '#1f2937', text: '#9ca3af' },
};

export default function JobCard({ job, index }: JobCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [coldMsg, setColdMsg] = useState(job.cold_message || '');
  const [loadingDM, setLoadingDM] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleColdDM = async () => {
    setLoadingDM(true);
    try {
      const res = await generateColdDM(job.id);
      setColdMsg(res.message);
      await navigator.clipboard.writeText(res.message);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setColdMsg('Failed to generate DM');
    } finally {
      setLoadingDM(false);
    }
  };

  const roleDomains = detectRoleDomains(job.role_title, job.role_category);
  const experienceLabel = formatExperience(job.experience_level);

  // Filter junk founders, then deduplicate by name (keep first occurrence)
  const realFounders = job.founders.filter(isRealFounder).reduce<Founder[]>((acc, f) => {
    const nameKey = f.name.trim().toLowerCase();
    if (!acc.some(existing => existing.name.trim().toLowerCase() === nameKey)) {
      acc.push(f);
    }
    return acc;
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
      className="job-card rounded-xl border cursor-pointer p-5"
      style={{
        backgroundColor: 'var(--color-card)',
        borderColor: 'var(--color-border)',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-base font-bold" style={{ color: 'var(--color-text)' }}>
            {job.company_name}
          </h3>
          <p className="text-sm mt-0.5" style={{ color: 'var(--color-accent)' }}>
            {job.role_title}
          </p>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0 flex-wrap justify-end">
          {job.batch && (
            <span
              className="badge"
              style={{ backgroundColor: 'var(--color-accent)', color: '#fff' }}
            >
              {job.batch}
            </span>
          )}
          {job.stage && (
            <span
              className="badge border"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
            >
              {job.stage}
            </span>
          )}
          {job.visa_sponsorship && job.visa_sponsorship !== 'Unknown' && (
            <span
              className="badge"
              style={{
                backgroundColor: job.visa_sponsorship === 'Yes' ? '#059669' : '#dc2626',
                color: '#fff',
              }}
            >
              Visa: {job.visa_sponsorship}
            </span>
          )}
        </div>
      </div>

      {/* Meta Row: salary, team size, funding, location, work type */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs mb-3" style={{ color: 'var(--color-muted)' }}>
        {job.salary_range && (
          <span className="font-medium" style={{ color: 'var(--color-text)' }}>
            💰 {job.salary_range}
          </span>
        )}
        {!job.salary_range && (
          <span>💰 Not disclosed</span>
        )}
        {job.team_size && job.team_size > 0 && (
          <span>👥 {job.team_size} employees</span>
        )}
        {job.founded_year && (
          <span>📅 Founded {job.founded_year}</span>
        )}
        {job.funding_total && (
          <span>💵 {job.funding_total}</span>
        )}
        {(job.country || job.city) && (
          <span>📍 {[job.city, job.country].filter(Boolean).join(', ')}</span>
        )}
        {job.work_type && (
          <span className="capitalize">🏢 {job.work_type}</span>
        )}
      </div>

      {/* VC Backers */}
      {job.vc_backers.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {job.vc_backers.filter(Boolean).map((vc, i) => (
            <span
              key={i}
              className="badge border"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)' }}
            >
              {vc}
            </span>
          ))}
        </div>
      )}

      {/* Industry Tags */}
      {job.industry_tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {job.industry_tags.slice(0, 4).map((tag, i) => (
            <span
              key={i}
              className="badge"
              style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-accent)' }}
            >
              {tag}
            </span>
          ))}
          {job.industry_tags.length > 4 && (
            <span className="badge" style={{ color: 'var(--color-muted)' }}>
              +{job.industry_tags.length - 4}
            </span>
          )}
        </div>
      )}

      {/* ═══ Enhanced Job Specification Box ═══ */}
      <div className="job-spec-box mb-3" style={{
        borderTop: '1px solid var(--color-border)',
        paddingTop: '0.75rem',
      }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-muted)' }}>
          Job Specification
        </p>

        {/* Role domain tags */}
        <div className="flex flex-wrap gap-1 mb-2">
          {roleDomains.map((domain, i) => {
            const colors = domainColors[domain] || domainColors['General'];
            return (
              <span
                key={i}
                className="badge"
                style={{
                  backgroundColor: colors.bg,
                  color: colors.text,
                  fontSize: '0.7rem',
                  padding: '0.2rem 0.55rem',
                  fontWeight: 600,
                }}
              >
                {domain}
              </span>
            );
          })}
        </div>

        {/* Compact info grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.35rem 0.75rem',
          padding: '0.5rem 0.65rem',
          borderRadius: '0.5rem',
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
        }}>
          {/* Experience */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)' }}>📊</span>
            <div>
              <span style={{ fontSize: '0.6rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Experience</span>
              <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text)', lineHeight: 1.2 }}>{experienceLabel}</p>
            </div>
          </div>

          {/* Salary */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)' }}>💰</span>
            <div>
              <span style={{ fontSize: '0.6rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Salary</span>
              <p style={{ fontSize: '0.75rem', fontWeight: 600, color: job.salary_range ? '#10b981' : 'var(--color-muted)', lineHeight: 1.2 }}>
                {job.salary_range || 'Not disclosed'}
              </p>
            </div>
          </div>

          {/* Sponsorship */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)' }}>🛂</span>
            <div>
              <span style={{ fontSize: '0.6rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Visa Sponsor</span>
              <p style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: job.visa_sponsorship === 'Yes' ? '#10b981' : job.visa_sponsorship === 'No' ? '#ef4444' : 'var(--color-muted)',
                lineHeight: 1.2,
              }}>
                {job.visa_sponsorship || 'Unknown'}
              </p>
            </div>
          </div>

          {/* Work Type */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-muted)' }}>🏢</span>
            <div>
              <span style={{ fontSize: '0.6rem', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Work Type</span>
              <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text)', lineHeight: 1.2, textTransform: 'capitalize' }}>
                {job.work_type || 'Not specified'}
              </p>
            </div>
          </div>
        </div>

        {/* JD Summary text */}
        {(job.jd_summary || job.job_description) && (
          <p className="text-sm leading-relaxed job-spec-preview" style={{ color: 'var(--color-muted)', marginTop: '0.5rem' }}>
            {job.jd_summary || (job.job_description ? job.job_description.slice(0, 200) + '...' : '')}
          </p>
        )}
      </div>

      {/* Founders block — only show REAL founders */}
      {realFounders.length > 0 && (
        <div className="mb-3" style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}>
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-muted)' }}>
            Founders
          </p>
          {realFounders.map((founder, i) => (
            <div key={i} className="flex items-center justify-between py-1">
              <div className="flex items-center gap-2">
                <span
                  className="flex items-center justify-center text-xs font-bold"
                  style={{
                    backgroundColor: 'var(--color-accent)',
                    color: '#fff',
                    width: '1.5rem',
                    height: '1.5rem',
                    borderRadius: '50%',
                  }}
                >
                  {founder.name.charAt(0).toUpperCase()}
                </span>
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                    {founder.name}
                  </p>
                  {founder.title && founder.title !== 'Team Member' && (
                    <p className="text-xs" style={{ color: 'var(--color-muted)' }}>
                      {founder.title}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {founder.linkedin && (
                  <a
                    href={founder.linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="founder-social-link"
                    title="LinkedIn"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="var(--color-accent)">
                      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                    </svg>
                  </a>
                )}
                {founder.twitter && (
                  <a
                    href={founder.twitter}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="founder-social-link"
                    title="Twitter/X"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="var(--color-accent)">
                      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                    </svg>
                  </a>
                )}
                {founder.email && (
                  <a
                    href={`mailto:${founder.email}`}
                    onClick={(e) => e.stopPropagation()}
                    className="founder-social-link"
                    title="Email"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="2">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="M22 4L12 13 2 4" />
                    </svg>
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Expanded: full JD */}
      {expanded && job.job_description && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mb-3"
          style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}
        >
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-muted)' }}>
            Full Description
          </p>
          <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--color-text)' }}>
            {job.job_description}
          </p>
        </motion.div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3" style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}>
        <button
          id={`cold-dm-${job.id}`}
          onClick={(e) => {
            e.stopPropagation();
            handleColdDM();
          }}
          disabled={loadingDM}
          className="px-3 py-1.5 rounded-lg text-xs font-medium border cursor-pointer"
          style={{
            borderColor: 'var(--color-accent)',
            color: 'var(--color-accent)',
            opacity: loadingDM ? 0.5 : 1,
            backgroundColor: 'transparent',
          }}
        >
          {loadingDM ? 'Generating...' : copied ? '✓ Copied!' : '📋 Copy Cold DM'}
        </button>

        {job.job_url && (
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-white"
            style={{ backgroundColor: 'var(--color-accent)', textDecoration: 'none' }}
          >
            Apply →
          </a>
        )}

        {job.company_website && (
          <a
            href={job.company_website}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="px-3 py-1.5 rounded-lg text-xs font-medium border"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-muted)', textDecoration: 'none' }}
          >
            🔗 Website
          </a>
        )}
      </div>

      {/* Cold DM preview */}
      {coldMsg && (
        <div
          className="mt-3 p-3 rounded-lg text-sm"
          style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text)' }}
        >
          <p className="text-xs font-semibold mb-1" style={{ color: 'var(--color-accent)' }}>
            Generated Cold DM:
          </p>
          {coldMsg}
        </div>
      )}
    </motion.div>
  );
}
