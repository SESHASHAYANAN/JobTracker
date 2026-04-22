/* ═══════════════════════════════════════════════════════
   Agent Types — mirrors Python agent models (Pydantic)
   ═══════════════════════════════════════════════════════ */

export type AgentStatus = 'idle' | 'running' | 'complete' | 'error';

export type Grade = 'A' | 'B' | 'C' | 'D' | 'E' | 'F';

export type Archetype =
  | 'llmops'
  | 'agentic'
  | 'technical_pm'
  | 'solutions_arch'
  | 'forward_deployed'
  | 'transformation'
  | 'general';

export type JobStatus =
  | 'Evaluated'
  | 'Applied'
  | 'Responded'
  | 'Interview'
  | 'Offer'
  | 'Rejected'
  | 'Discarded'
  | 'SKIP';

export type BatchJobStatus = 'pending' | 'processing' | 'completed' | 'failed';

// ── Scan ────────────────────────────────────────────────

export interface ScannedJob {
  title: string;
  url: string;
  company: string;
  location: string;
  source: string;
  discovered_at: string;
}

export interface ScanResponse {
  status: string;
  date: string;
  companies_scanned: number;
  total_found: number;
  filtered_by_title: number;
  duplicates: number;
  new_offers: ScannedJob[];
  errors: { company: string; error: string }[];
}

// ── Score ────────────────────────────────────────────────

export interface DimensionScore {
  name: string;
  score: number;
  weight: number;
  reasoning: string;
  evidence: string[];
}

export interface ScoreResponse {
  status: string;
  error?: string;
  company: string;
  role: string;
  archetype: Archetype;
  archetype_confidence: number;
  dimensions: DimensionScore[];
  overall_score: number;
  grade: Grade;
  recommendation: string;
  cv_match_summary: string;
  gaps: string[];
  gap_mitigations: string[];
  keywords: string[];
  report_path: string;
}

// ── Tailor ──────────────────────────────────────────────

export interface TailoredSection {
  name: string;
  original: string;
  tailored: string;
  keywords_used: string[];
}

export interface TailorResponse {
  status: string;
  error?: string;
  sections: TailoredSection[];
  keywords_injected: string[];
  keyword_coverage: number;
  ats_score: number;
  html_path: string | null;
  pdf_path: string | null;
  page_count: number;
}

// ── Batch ───────────────────────────────────────────────

export interface BatchJob {
  id: number;
  url: string;
  status: BatchJobStatus;
  started_at: string | null;
  completed_at: string | null;
  report_num: number | null;
  score: number | null;
  error: string | null;
  retries: number;
}

export interface BatchResponse {
  status: string;
  error?: string;
  total: number;
  completed: number;
  failed: number;
  skipped: number;
  elapsed_seconds: number;
  results: BatchJob[];
}

export interface BatchStatusResponse {
  status: string;
  total: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  avg_score: number;
}

// ── Tracker ─────────────────────────────────────────────

export interface PipelineEntry {
  number: number;
  date: string;
  company: string;
  role: string;
  score: number | null;
  status: JobStatus;
  pdf_generated: boolean;
  report_link: string | null;
  notes: string;
}

export interface TrackerSummary {
  total_entries: number;
  by_status: Record<string, number>;
  avg_score: number;
  top_companies: string[];
  last_updated: string | null;
}

export interface TrackerResponse {
  status: string;
  entries: PipelineEntry[];
  summary: TrackerSummary;
}

export interface PipelineAnalytics {
  summary: TrackerSummary;
  conversion_rates: Record<string, number>;
  score_distribution: Record<string, number>;
  archetype_breakdown: Record<string, number>;
  weekly_activity: Record<string, unknown>[];
  insights: string[];
}

export interface AnalyticsResponse {
  status: string;
  analytics: PipelineAnalytics;
}

// ── Health ──────────────────────────────────────────────

export interface AgentHealthResponse {
  status: string;
  warnings: string[];
  cv_loaded: boolean;
  data_dir: string;
}
