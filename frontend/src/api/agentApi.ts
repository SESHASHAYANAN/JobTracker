/**
 * Agent API client — all HTTP calls to /api/agents/* endpoints.
 *
 * Each function returns the parsed JSON response from the backend.
 * The backend wraps each agent call in try/catch and always returns
 * { status: "ok"|"error", ... }.
 */
import type {
  ScanResponse,
  ScoreResponse,
  TailorResponse,
  BatchResponse,
  BatchStatusResponse,
  TrackerResponse,
  AnalyticsResponse,
  AgentHealthResponse,
} from '../types/agentTypes';

const BASE = '/api/agents';

// ── Health ──────────────────────────────────────────────

export async function fetchAgentHealth(): Promise<AgentHealthResponse> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`Agent health check failed: ${res.status}`);
  return res.json();
}

// ── Scan ────────────────────────────────────────────────

export async function runScan(
  company?: string,
  dryRun = false,
): Promise<ScanResponse> {
  const res = await fetch(`${BASE}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company: company || null, dry_run: dryRun }),
  });
  if (!res.ok) throw new Error(`Scan failed: ${res.status}`);
  return res.json();
}

// ── Score ────────────────────────────────────────────────

export async function runScore(params: {
  url?: string;
  jd_text?: string;
  cv_text?: string;
  company?: string;
  role?: string;
}): Promise<ScoreResponse> {
  const res = await fetch(`${BASE}/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Score failed: ${res.status}`);
  return res.json();
}

// ── Tailor ──────────────────────────────────────────────

export async function runTailor(params: {
  url?: string;
  jd_text?: string;
  cv_text?: string;
  company?: string;
  role?: string;
}): Promise<TailorResponse> {
  const res = await fetch(`${BASE}/tailor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Tailor failed: ${res.status}`);
  return res.json();
}

// ── Batch ───────────────────────────────────────────────

export async function runBatch(params: {
  urls: string[];
  cv_text?: string;
  concurrency?: number;
}): Promise<BatchResponse> {
  const res = await fetch(`${BASE}/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Batch failed: ${res.status}`);
  return res.json();
}

export async function fetchBatchStatus(): Promise<BatchStatusResponse> {
  const res = await fetch(`${BASE}/batch/status`);
  if (!res.ok) throw new Error(`Batch status failed: ${res.status}`);
  return res.json();
}

// ── Tracker ─────────────────────────────────────────────

export async function fetchTracker(
  statusFilter?: string,
): Promise<TrackerResponse> {
  const params = new URLSearchParams();
  if (statusFilter) params.set('status', statusFilter);
  const qs = params.toString();
  const res = await fetch(`${BASE}/tracker${qs ? '?' + qs : ''}`);
  if (!res.ok) throw new Error(`Tracker fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchAnalytics(): Promise<AnalyticsResponse> {
  const res = await fetch(`${BASE}/tracker/analytics`);
  if (!res.ok) throw new Error(`Analytics fetch failed: ${res.status}`);
  return res.json();
}

export async function updateTrackerStatus(
  company: string,
  role: string,
  newStatus: string,
): Promise<{ status: string; updated: boolean }> {
  const res = await fetch(`${BASE}/tracker/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company, role, new_status: newStatus }),
  });
  if (!res.ok) throw new Error(`Status update failed: ${res.status}`);
  return res.json();
}
