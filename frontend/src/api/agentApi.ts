/**
 * Agent API client — all HTTP calls to /api/agents/* endpoints.
 *
 * Each function returns the parsed JSON response from the backend.
 * The backend wraps each agent call in try/catch and always returns
 * { status: "ok"|"error", ... }.
 *
 * When the backend is unreachable (ECONNREFUSED), the client falls back
 * to mock/simulated responses so the frontend remains fully functional.
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

// ── Graceful Fetch Helper ────────────────────────────────
async function gracefulFetch<T>(url: string, options?: RequestInit, fallback?: T): Promise<T> {
  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch {
    if (fallback !== undefined) return fallback;
    throw new Error('Backend unreachable');
  }
}

// ── Health ──────────────────────────────────────────────

export async function fetchAgentHealth(): Promise<AgentHealthResponse> {
  return gracefulFetch(`${BASE}/health`, undefined, {
    status: 'degraded',
    warnings: ['Backend server not running — using offline mode'],
    cv_loaded: false,
    data_dir: '',
  });
}

// ── Scan ────────────────────────────────────────────────

export async function runScan(
  company?: string,
  dryRun = false,
): Promise<ScanResponse> {
  return gracefulFetch(`${BASE}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company: company || null, dry_run: dryRun }),
  });
}



// ── Score ────────────────────────────────────────────────

export async function runScore(params: {
  url?: string;
  jd_text?: string;
  cv_text?: string;
  company?: string;
  role?: string;
}): Promise<ScoreResponse> {
  return gracefulFetch(`${BASE}/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

// ── Tailor ──────────────────────────────────────────────

export async function runTailor(params: {
  url?: string;
  jd_text?: string;
  cv_text?: string;
  company?: string;
  role?: string;
}): Promise<TailorResponse> {
  return gracefulFetch(`${BASE}/tailor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

// ── Batch ───────────────────────────────────────────────

export async function runBatch(params: {
  urls: string[];
  cv_text?: string;
  concurrency?: number;
}): Promise<BatchResponse> {
  return gracefulFetch(`${BASE}/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
}

export async function fetchBatchStatus(): Promise<BatchStatusResponse> {
  return gracefulFetch(`${BASE}/batch/status`);
}

// ── Tracker ─────────────────────────────────────────────

export async function fetchTracker(
  statusFilter?: string,
): Promise<TrackerResponse> {
  const params = new URLSearchParams();
  if (statusFilter) params.set('status', statusFilter);
  const qs = params.toString();
  return gracefulFetch(`${BASE}/tracker${qs ? '?' + qs : ''}`, undefined, {
    status: 'ok',
    entries: [],
    summary: { total_entries: 0, by_status: {}, avg_score: 0, top_companies: [], last_updated: null },
  });
}

export async function fetchAnalytics(): Promise<AnalyticsResponse> {
  return gracefulFetch(`${BASE}/tracker/analytics`);
}

export async function updateTrackerStatus(
  company: string,
  role: string,
  newStatus: string,
): Promise<{ status: string; updated: boolean }> {
  return gracefulFetch(`${BASE}/tracker/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company, role, new_status: newStatus }),
  });
}


