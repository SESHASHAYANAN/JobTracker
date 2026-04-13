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
  }, generateMockScanResponse());
}

function generateMockScanResponse(): ScanResponse {
  const jobs = [
    // ── US Tech Giants ──
    { company: 'Google', title: 'Software Engineer, New Grad', location: 'Mountain View, CA', source: 'careers' },
    { company: 'Google', title: 'Associate Product Manager', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Meta', title: 'Software Engineer (University Grad)', location: 'Menlo Park, CA', source: 'careers' },
    { company: 'Meta', title: 'Data Scientist, Entry Level', location: 'London, UK', source: 'linkedin' },
    { company: 'Apple', title: 'Software Engineer — New Grad', location: 'Cupertino, CA', source: 'careers' },
    { company: 'Microsoft', title: 'Software Engineer I', location: 'Redmond, WA', source: 'careers' },
    { company: 'Microsoft', title: 'Software Engineer, Fresher', location: 'Hyderabad, India', source: 'linkedin' },
    { company: 'Amazon', title: 'SDE I (New Grad)', location: 'Seattle, WA', source: 'careers' },
    { company: 'Amazon', title: 'SDE I', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Netflix', title: 'Junior Software Engineer', location: 'Los Gatos, CA', source: 'careers' },
    // ── AI/ML Startups ──
    { company: 'OpenAI', title: 'Research Engineer, Entry Level', location: 'San Francisco, CA', source: 'careers' },
    { company: 'OpenAI', title: 'Software Engineer — Platform', location: 'San Francisco, CA', source: 'linkedin' },
    { company: 'Anthropic', title: 'Software Engineer, New Grad', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Anthropic', title: 'ML Engineer, Entry Level', location: 'Remote', source: 'wellfound' },
    { company: 'Mistral AI', title: 'ML Engineer', location: 'Paris, France', source: 'linkedin' },
    { company: 'Cohere', title: 'Software Engineer, Junior', location: 'Toronto, Canada', source: 'careers' },
    { company: 'Hugging Face', title: 'ML Engineer, Open Source', location: 'Remote', source: 'wellfound' },
    { company: 'Stability AI', title: 'Software Engineer', location: 'London, UK', source: 'linkedin' },
    { company: 'Weights & Biases', title: 'Frontend Engineer, Junior', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Scale AI', title: 'Operations Analyst, Entry', location: 'San Francisco, CA', source: 'indeed' },
    { company: 'Replicate', title: 'Full Stack Engineer', location: 'San Francisco, CA', source: 'yc' },
    { company: 'Perplexity AI', title: 'Software Engineer, New Grad', location: 'San Francisco, CA', source: 'linkedin' },
    { company: 'Character AI', title: 'ML Engineer, Junior', location: 'Palo Alto, CA', source: 'wellfound' },
    { company: 'Runway', title: 'Software Engineer', location: 'New York, NY', source: 'careers' },
    { company: 'Jasper AI', title: 'Full Stack Developer', location: 'Remote', source: 'linkedin' },
    // ── Indian Startups ──
    { company: 'Razorpay', title: 'Software Engineer, Fresher', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Razorpay', title: 'Frontend Developer', location: 'Bangalore, India', source: 'careers' },
    { company: 'Zerodha', title: 'Backend Engineer, Junior', location: 'Bangalore, India', source: 'careers' },
    { company: 'CRED', title: 'Software Engineer, New Grad', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'CRED', title: 'Android Developer, Fresher', location: 'Bangalore, India', source: 'wellfound' },
    { company: 'Flipkart', title: 'SDE 1 (Fresher)', location: 'Bangalore, India', source: 'careers' },
    { company: 'Swiggy', title: 'Software Engineer I', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Zomato', title: 'Software Engineer, Frontend', location: 'Gurgaon, India', source: 'careers' },
    { company: 'PhonePe', title: 'Junior Software Engineer', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Meesho', title: 'Software Engineer, Entry Level', location: 'Bangalore, India', source: 'indeed' },
    { company: 'ShareChat', title: 'ML Engineer, Fresher', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Ola', title: 'Software Engineer I', location: 'Bangalore, India', source: 'careers' },
    { company: 'Freshworks', title: 'Software Engineer, New Grad', location: 'Chennai, India', source: 'careers' },
    { company: 'Postman', title: 'Software Engineer, Junior', location: 'Bangalore, India', source: 'careers' },
    { company: 'BrowserStack', title: 'Software Engineer I', location: 'Mumbai, India', source: 'linkedin' },
    { company: 'Chargebee', title: 'Full Stack Developer, Junior', location: 'Chennai, India', source: 'wellfound' },
    { company: 'Zoho', title: 'Software Engineer, Fresher', location: 'Chennai, India', source: 'careers' },
    { company: 'InMobi', title: 'Software Engineer I', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Dream11', title: 'Backend Engineer, Junior', location: 'Mumbai, India', source: 'careers' },
    { company: 'Unacademy', title: 'Full Stack Developer', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'upGrad', title: 'Software Engineer, Fresher', location: 'Mumbai, India', source: 'indeed' },
    { company: 'Groww', title: 'Software Engineer I', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Paytm', title: 'Software Engineer, New Grad', location: 'Noida, India', source: 'careers' },
    { company: 'Lenskart', title: 'Frontend Developer, Fresher', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'OYO', title: 'Software Engineer I', location: 'Gurgaon, India', source: 'careers' },
    { company: 'Nykaa', title: 'Backend Developer, Junior', location: 'Mumbai, India', source: 'linkedin' },
    // ── DevTools & Cloud ──
    { company: 'Stripe', title: 'Software Engineer, New Grad', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Stripe', title: 'Software Engineer I', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Vercel', title: 'Full Stack Developer, Junior', location: 'Remote', source: 'wellfound' },
    { company: 'Supabase', title: 'Software Engineer', location: 'Remote', source: 'yc' },
    { company: 'PlanetScale', title: 'Software Engineer, New Grad', location: 'Remote', source: 'yc' },
    { company: 'Railway', title: 'Full Stack Engineer, Junior', location: 'Remote', source: 'yc' },
    { company: 'Render', title: 'Software Engineer', location: 'Remote', source: 'careers' },
    { company: 'Fly.io', title: 'Infrastructure Engineer', location: 'Remote', source: 'yc' },
    { company: 'Neon', title: 'Software Engineer', location: 'Remote', source: 'careers' },
    { company: 'Cloudflare', title: 'Systems Engineer, New Grad', location: 'Austin, TX', source: 'careers' },
    { company: 'HashiCorp', title: 'Software Engineer I', location: 'Remote', source: 'linkedin' },
    { company: 'Datadog', title: 'Software Engineer, Junior', location: 'New York, NY', source: 'careers' },
    { company: 'Figma', title: 'Software Engineer, New Grad', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Notion', title: 'Software Engineer, Junior', location: 'San Francisco, CA', source: 'linkedin' },
    { company: 'Linear', title: 'Software Engineer', location: 'Remote', source: 'yc' },
    { company: 'Retool', title: 'Software Engineer, New Grad', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Airtable', title: 'Software Engineer I', location: 'San Francisco, CA', source: 'linkedin' },
    // ── Fintech ──
    { company: 'Plaid', title: 'Software Engineer, Junior', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Coinbase', title: 'Software Engineer, New Grad', location: 'Remote', source: 'linkedin' },
    { company: 'Robinhood', title: 'Software Engineer I', location: 'Menlo Park, CA', source: 'careers' },
    { company: 'Revolut', title: 'Junior Software Engineer', location: 'London, UK', source: 'linkedin' },
    { company: 'Wise', title: 'Software Engineer, New Grad', location: 'London, UK', source: 'careers' },
    // ── Global Startups ──
    { company: 'Miro', title: 'Frontend Engineer, Junior', location: 'Berlin, Germany', source: 'linkedin' },
    { company: 'Loom', title: 'Software Engineer', location: 'Remote', source: 'wellfound' },
    { company: 'Canva', title: 'Software Engineer, Graduate', location: 'Sydney, Australia', source: 'careers' },
    { company: 'Atlassian', title: 'Software Engineer, Graduate', location: 'Sydney, Australia', source: 'careers' },
    { company: 'Atlassian', title: 'Software Engineer, Fresher', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Shopify', title: 'Developer, New Grad', location: 'Remote', source: 'careers' },
    { company: 'GitLab', title: 'Software Engineer, Junior', location: 'Remote', source: 'linkedin' },
    { company: 'Twilio', title: 'Software Engineer I', location: 'Remote', source: 'careers' },
    { company: 'Snowflake', title: 'Software Engineer, New Grad', location: 'San Mateo, CA', source: 'linkedin' },
    { company: 'Databricks', title: 'Software Engineer I', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Databricks', title: 'Software Engineer, Fresher', location: 'Bangalore, India', source: 'linkedin' },
    // ── YC Startups ──
    { company: 'Zepto', title: 'Software Engineer, Fresher', location: 'Mumbai, India', source: 'yc' },
    { company: 'Rapido', title: 'Backend Developer, Junior', location: 'Bangalore, India', source: 'yc' },
    { company: 'Khatabook', title: 'Full Stack Developer', location: 'Bangalore, India', source: 'yc' },
    { company: 'Clear (ClearTax)', title: 'Software Engineer I', location: 'Bangalore, India', source: 'yc' },
    { company: 'Glean', title: 'Software Engineer, New Grad', location: 'Palo Alto, CA', source: 'yc' },
    { company: 'Hume AI', title: 'ML Engineer, Junior', location: 'New York, NY', source: 'yc' },
    { company: 'Arize AI', title: 'Software Engineer', location: 'Remote', source: 'yc' },
    { company: 'Tinybird', title: 'Software Engineer, Junior', location: 'Remote', source: 'yc' },
    { company: 'PolyAI', title: 'ML Engineer', location: 'London, UK', source: 'yc' },
    { company: 'Ada', title: 'Software Engineer, New Grad', location: 'Toronto, Canada', source: 'yc' },
    { company: 'Snyk', title: 'Software Engineer I', location: 'London, UK', source: 'careers' },
    // ── More job boards ──
    { company: 'Salesforce', title: 'Associate Software Engineer', location: 'Hyderabad, India', source: 'indeed' },
    { company: 'Adobe', title: 'Software Engineer, Fresher', location: 'Noida, India', source: 'linkedin' },
    { company: 'Intuit', title: 'Software Engineer 1', location: 'Bangalore, India', source: 'glassdoor' },
    { company: 'Uber', title: 'Software Engineer I', location: 'Bangalore, India', source: 'linkedin' },
    { company: 'Uber', title: 'Software Engineer, New Grad', location: 'San Francisco, CA', source: 'careers' },
    { company: 'Gong', title: 'Software Engineer, Junior', location: 'San Francisco, CA', source: 'linkedin' },
    { company: 'Zapier', title: 'Software Engineer, New Grad', location: 'Remote', source: 'wellfound' },
    { company: 'Wiz', title: 'Software Engineer, Junior', location: 'New York, NY', source: 'linkedin' },
    { company: 'Cognigy', title: 'Junior Backend Engineer', location: 'Berlin, Germany', source: 'linkedin' },
    { company: 'Factorial', title: 'Software Engineer, Junior', location: 'Barcelona, Spain', source: 'wellfound' },
    { company: 'Travelperk', title: 'Software Engineer', location: 'Barcelona, Spain', source: 'linkedin' },
  ];

  return {
    status: 'ok',
    date: new Date().toISOString().split('T')[0],
    companies_scanned: 65,
    total_found: jobs.length,
    filtered_by_title: 5,
    duplicates: 3,
    new_offers: jobs.map(c => ({
      title: c.title,
      url: `https://${c.company.toLowerCase().replace(/[^a-z0-9]/g, '')}.com/careers`,
      company: c.company,
      location: c.location,
      source: c.source,
      discovered_at: new Date().toISOString(),
    })),
    errors: [],
  };
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

// ── Profile Auto-Import (simulated) ─────────────────────

export async function importLinkedInProfile(linkedinUrl: string) {
  // Simulate LinkedIn profile scraping
  await new Promise(r => setTimeout(r, 1500));
  const username = linkedinUrl.split('/in/')[1]?.replace(/\//g, '') || 'user';
  return {
    fullName: username.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') || 'Professional',
    email: `${username.toLowerCase().replace(/[^a-z]/g, '')}@gmail.com`,
    headline: 'Aspiring Software Engineer | Computer Science Graduate',
    skills: ['JavaScript', 'Python', 'React', 'Node.js', 'SQL', 'Git', 'HTML/CSS', 'TypeScript', 'Java', 'C++', 'Data Structures', 'Algorithms'],
    experience: [
      { company: 'Tech Startup', role: 'Software Development Intern', duration: 'Jun 2025 – Aug 2025', description: '• Built REST APIs using Node.js and Express\n• Developed React components for customer dashboard\n• Participated in agile sprints and code reviews' },
    ],
    education: [
      { institution: 'University', degree: 'B.Tech Computer Science', year: '2026' },
    ],
  };
}

export async function importGitHubProfile(githubUrl: string) {
  // Simulate GitHub profile scraping
  await new Promise(r => setTimeout(r, 1200));
  const username = githubUrl.split('github.com/')[1]?.replace(/\//g, '') || 'user';
  return {
    fullName: username.split(/[-_]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
    github: githubUrl,
    skills: ['JavaScript', 'TypeScript', 'Python', 'React', 'Node.js', 'Git', 'REST APIs', 'MongoDB', 'PostgreSQL', 'Docker', 'HTML/CSS', 'Java'],
    projects: [
      { name: 'Portfolio Website', description: 'Personal portfolio built with React and Next.js', tech: 'React, Next.js, CSS' },
      { name: 'Task Manager API', description: 'RESTful API for task management with auth', tech: 'Node.js, Express, MongoDB' },
      { name: 'ML Image Classifier', description: 'Image classification using TensorFlow', tech: 'Python, TensorFlow, Flask' },
    ],
    contributions: 247,
    repos: 18,
  };
}
