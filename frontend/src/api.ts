import { JobsResponse, ColdMessageResponse, Filters, ResumeUploadResponse, ColdEmailResponse, ApplicationProfile, ApplicationRecord, AutoApplyConfig, DashboardStats, ApplyResponse } from './types';

const BASE = '/api';

export async function fetchJobs(filters: Filters, page = 1, limit = 30): Promise<JobsResponse> {
  const params = new URLSearchParams();
  if (filters.role) params.set('role', filters.role);
  if (filters.visa) params.set('visa', filters.visa);
  if (filters.country) params.set('country', filters.country);
  if (filters.stage) params.set('stage', filters.stage);
  if (filters.vc) params.set('vc', filters.vc);
  if (filters.batch) params.set('batch', filters.batch);
  if (filters.level) params.set('level', filters.level);
  if (filters.team_size_bucket) params.set('team_size_bucket', filters.team_size_bucket);
  if (filters.founder_name) params.set('founder_name', filters.founder_name);
  if (filters.search) params.set('search', filters.search);
  // New startup filters
  if (filters.startup_only) params.set('startup_only', 'true');
  if (filters.stealth_only) params.set('stealth_only', 'true');
  if (filters.engineering_only) params.set('engineering_only', 'true');
  if (filters.india_only) params.set('india_only', 'true');
  if (filters.founding_only) params.set('founding_only', 'true');
  if (filters.min_match_score) params.set('min_match_score', String(filters.min_match_score));
  if (filters.apply_mode_filter) params.set('apply_mode_filter', filters.apply_mode_filter);
  if (filters.offers_relocation) params.set('offers_relocation', 'true');
  if (filters.remote_india) params.set('remote_india', 'true');
  params.set('page', String(page));
  params.set('limit', String(limit));

  try {
    const res = await fetch(`${BASE}/jobs?${params.toString()}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  } catch {
    // Backend unreachable — return empty results to prevent retry storms
    return { jobs: [], total: 0, page, limit, has_more: false };
  }
}

export async function generateColdDM(jobId: string, candidateProfile?: string): Promise<ColdMessageResponse> {
  const res = await fetch(`${BASE}/cold-message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, candidate_profile: candidateProfile }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  return res.json();
}

export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE}/resume/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload error: ${res.status}`);
  return res.json();
}

export async function generateColdEmail(jobId: string, resumeText: string): Promise<ColdEmailResponse> {
  const formData = new FormData();
  formData.append('job_id', jobId);
  formData.append('resume_text', resumeText);
  const res = await fetch(`${BASE}/resume/cold-email`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Email generation error: ${res.status}`);
  return res.json();
}


// ── Application Profile ────────────────────────────────

export async function saveProfile(profile: ApplicationProfile) {
  const res = await fetch(`${BASE}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
  return res.json();
}

export async function getProfile(): Promise<{ status: string; profile: ApplicationProfile | null }> {
  const res = await fetch(`${BASE}/profile`);
  return res.json();
}

// ── Apply ────────────────────────────────────────────────

export async function applyToJob(jobId: string): Promise<ApplyResponse & {
  url_source?: string;
  live_verified?: boolean;
  verification_steps?: { step: string; status: string; timestamp: string; detail: string }[];
}> {
  const res = await fetch(`${BASE}/apply/${jobId}`, { method: 'POST' });
  return res.json();
}

export async function verifyUrlLive(url: string): Promise<{
  reachable: boolean;
  status_code?: number;
  final_url?: string;
  is_job_page?: boolean;
  page_title?: string;
  can_iframe?: boolean;
  reason?: string;
}> {
  const res = await fetch(`${BASE}/verify-url?url=${encodeURIComponent(url)}`);
  return res.json();
}

export function getProxyPageUrl(url: string): string {
  return `${BASE}/proxy-page?url=${encodeURIComponent(url)}`;
}

