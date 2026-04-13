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
