import { JobsResponse, ColdMessageResponse, Filters, ResumeUploadResponse, ColdEmailResponse } from './types';

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

