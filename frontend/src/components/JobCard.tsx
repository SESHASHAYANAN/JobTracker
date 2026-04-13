import { useState } from 'react';
import { motion } from 'framer-motion';
import { Job } from '../types';
import { generateColdDM } from '../api';

interface JobCardProps {
  job: Job;
  index: number;
}

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

      {/* Job Specification Preview — always visible */}
      {(job.jd_summary || job.job_description) && (
        <div className="mb-3" style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}>
          <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--color-muted)' }}>
            Job Specification
          </p>
          <p className="text-sm leading-relaxed job-spec-preview" style={{ color: 'var(--color-muted)' }}>
            {job.jd_summary || (job.job_description ? job.job_description.slice(0, 200) + '...' : '')}
          </p>
        </div>
      )}

      {/* Founders block — ALWAYS visible if founders exist */}
      {job.founders.length > 0 && (
        <div className="mb-3" style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}>
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-muted)' }}>
            Founders
          </p>
          {job.founders.map((founder, i) => (
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
                  {founder.title && (
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
