export interface Founder {
  name: string;
  title: string;
  linkedin?: string | null;
  twitter?: string | null;
  email?: string | null;
  source: string;
}

export interface Job {
  id: string;
  company_name: string;
  company_website?: string | null;
  company_slug: string;
  batch?: string | null;
  stage?: string | null;
  vc_backers: string[];
  team_size?: number | null;
  founded_year?: number | null;
  funding_total?: string | null;
  status: string;
  is_hiring: boolean;
  role_title: string;
  role_category?: string | null;
  experience_level?: string | null;
  visa_sponsorship?: string | null;
  salary_range?: string | null;
  work_type?: string | null;
  country?: string | null;
  city?: string | null;
  job_url?: string | null;
  job_description?: string | null;
  jd_summary?: string | null;
  source: string;
  scraped_at: string;
  founders: Founder[];
  cold_message?: string | null;
  relevance_score: number;
  industry_tags: string[];
  // Startup classification
  is_startup: boolean;
  is_stealth: boolean;
  startup_stage?: string | null;
  startup_tags: string[];
  startup_confidence: number;
  // Resume match
  match_score?: number | null;
  match_reasons: string[];
  // Application
  apply_mode: string;
  // Freshness
  posted_date?: string | null;
  last_seen?: string | null;
  source_url?: string | null;
  // Relocation
  offers_relocation: boolean;
  relocation_countries: string[];
}

export interface JobsResponse {
  jobs: Job[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface Filters {
  role?: string;
  visa?: string;
  country?: string;
  stage?: string;
  vc?: string;
  batch?: string;
  level?: string;
  team_size_bucket?: string;
  founder_name?: string;
  search?: string;
  // New startup filters
  startup_only?: boolean;
  stealth_only?: boolean;
  engineering_only?: boolean;
  india_only?: boolean;
  founding_only?: boolean;
  min_match_score?: number;
  apply_mode_filter?: string;
  offers_relocation?: boolean;
  remote_india?: boolean;
}

export interface ColdMessageResponse {
  job_id: string;
  message: string;
  founder_name?: string;
}

export interface ResumeMatch {
  job: Job;
  match_score: number;
  matched_skills: string[];
  reasons: string[];
}

export interface ResumeProfile {
  skills: string[];
  experience_level: string;
  role_preferences: string[];
  resume_length: number;
}

export interface ResumeUploadResponse {
  matches: ResumeMatch[];
  profile: ResumeProfile;
  total_matched: number;
  error?: string;
}

export interface ColdEmailResponse {
  email: string;
  founder_name: string;
  founder_email?: string | null;
  founder_linkedin?: string | null;
  company_name: string;
  role_title: string;
  error?: string;
}

// ── Application Types ───────────────────────────────────

export interface ApplicationProfile {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  work_authorization: string;
  notice_period: string;
  years_of_experience: number;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  resume_text: string;
  cover_letter_template: string;
  preferred_titles: string[];
  preferred_cities: string[];
  preferred_stages: string[];
  preferred_tech_stack: string[];
  remote_preference: string;
  salary_expectation: string;
  blacklist_companies: string[];
  blacklist_domains: string[];
  include_stealth: boolean;
  auto_apply_mode: string;
}

export interface ApplicationStep {
  step: string;
  status: string;
  timestamp: string;
  detail: string;
}

export interface ApplicationRecord {
  id: string;
  job_id: string;
  company_name: string;
  role_title: string;
  status: string;
  applied_at: string;
  source: string;
  method: string;
  apply_url: string;
  error_message: string;
  email_sent: boolean;
  email_sent_at?: string | null;
  steps: ApplicationStep[];
  match_score: number;
}

export interface AutoApplyConfig {
  enabled: boolean;
  startup_only: boolean;
  india_only: boolean;
  remote_india: boolean;
  engineering_only: boolean;
  min_match_score: number;
  salary_min?: string | null;
  max_days_old: number;
  whitelist_companies: string[];
  blacklist_companies: string[];
  approval_mode: string;
  max_daily_applications: number;
  paused: boolean;
}

export interface DashboardStats {
  total_jobs: number;
  total_startup_jobs: number;
  startup_percentage: number;
  india_jobs: number;
  engineering_jobs: number;
  auto_apply_eligible: number;
  applications_sent: number;
  pending_approvals: number;
  failed_applications: number;
  emails_sent: number;
  top_tech_stacks: { name: string; count: number }[];
  top_startup_domains: { name: string; count: number }[];
  stealth_jobs: number;
  relocation_jobs: number;
}

export interface ApplyResponse {
  status: string;
  application: ApplicationRecord;
  email: { success: boolean; message: string };
  apply_url: string;
  error?: string;
}
