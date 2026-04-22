import { useState } from 'react';
import { motion } from 'framer-motion';
import { Job, Founder } from '../types';
import { generateColdDM } from '../api';
import LiveApplyPopup from './LiveApplyPopup';

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
  const [showApply, setShowApply] = useState(false);

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
      className={`job-card rounded-xl border cursor-pointer p-5 ${(job.match_score ?? 0) >= 80 ? 'recommended-card' : ''}`}
      style={{
        backgroundColor: 'var(--color-card)',
        borderColor: (job.match_score ?? 0) >= 80 ? 'transparent' : 'var(--color-border)',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-base font-bold" style={{ color: 'var(--color-text)' }}>
            {(job.match_score ?? 0) >= 80 && <span className="recommended-badge">⭐ Recommended</span>}
        </button>

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

      {/* Live Apply Popup */}
      {showApply && (
        <LiveApplyPopup job={job} open={showApply} onClose={() => setShowApply(false)} />
      )}

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
