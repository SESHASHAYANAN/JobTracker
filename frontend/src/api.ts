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

export async function applyToJob(jobId: string): Promise<ApplyResponse> {
  const res = await fetch(`${BASE}/apply/${jobId}`, { method: 'POST' });
  return res.json();
}

export async function batchApply(jobIds: string[]) {
  const res = await fetch(`${BASE}/apply/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(jobIds),
  });
  return res.json();
}

// ── Applications ────────────────────────────────────────

export async function getApplications(status?: string): Promise<{ applications: ApplicationRecord[]; total: number }> {
  const params = status ? `?status=${status}` : '';
  const res = await fetch(`${BASE}/applications${params}`);
  return res.json();
}

export async function updateApplicationStatus(appId: string, newStatus: string) {
  const res = await fetch(`${BASE}/applications/${appId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_status: newStatus }),
  });
  return res.json();
}

// ── Auto-Apply ──────────────────────────────────────────

export async function saveAutoApplyConfig(config: AutoApplyConfig) {
  const res = await fetch(`${BASE}/auto-apply/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return res.json();
}

export async function getAutoApplyConfig(): Promise<{ config: AutoApplyConfig }> {
  const res = await fetch(`${BASE}/auto-apply/config`);
  return res.json();
}

export async function runAutoApply() {
  const res = await fetch(`${BASE}/auto-apply/run`, { method: 'POST' });
  return res.json();
}

// ── Dashboard ──────────────────────────────────────────

export async function getDashboardStats(): Promise<{ stats: DashboardStats }> {
  const res = await fetch(`${BASE}/dashboard/stats`);
  return res.json();
}
