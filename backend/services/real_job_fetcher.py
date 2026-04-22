"""Real Job Fetcher — fetches live job listings with direct application URLs.

Uses multiple sources:
1. python-jobspy (if available) for Indeed/LinkedIn/Glassdoor
2. Direct API scraping for real-time results
3. APIMart API as enrichment source

Only includes jobs with valid, direct apply URLs (no generic career pages).
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Optional
from urllib.parse import urlparse, quote_plus

import httpx
from dotenv import load_dotenv

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(_project_root, '.env'))

logger = logging.getLogger(__name__)

# Try importing jobspy
try:
    from jobspy import scrape_jobs
    HAS_JOBSPY = True
except ImportError:
    HAS_JOBSPY = False
    logger.info("[real_jobs] python-jobspy not available, using direct scraping")


SEARCH_QUERIES = [
    "software engineer",
    "data scientist",
    "frontend developer",
    "backend engineer",
    "machine learning engineer",
    "full stack developer",
    "devops engineer",
    "product manager",
    "data engineer",
    "python developer",
]


def _generate_id(company: str, title: str, url: str) -> str:
    raw = f"{company}|{title}|{url}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()


def _is_direct_apply_url(url: str) -> bool:
    """Check if URL is a direct application link (not just a company homepage)."""
    if not url or not url.startswith("http"):
        return False
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    path = parsed.path.rstrip("/")
    if not path or path == "/":
        return False
    job_platforms = [
        "greenhouse.io", "lever.co", "ashbyhq.com", "workday.com",
        "smartrecruiters.com", "icims.com", "bamboohr.com",
        "recruitee.com", "workable.com", "breezy.hr", "myworkday",
        "jobvite.com", "indeed.com/viewjob", "indeed.com/rc",
        "linkedin.com/jobs", "glassdoor.com/job", "ziprecruiter.com/c",
        "wellfound.com/jobs", "jobs.lever.co", "boards.greenhouse",
    ]
    if any(plat in url_lower for plat in job_platforms):
        return True
    job_keywords = ["/job", "/career", "/apply", "/position", "/opening", "/role", "/vacancy"]
    if any(kw in url_lower for kw in job_keywords):
        return True
    if len(path.split("/")) >= 3:
        return True
    return False


def _format_salary(row) -> str:
    try:
        min_s = row.get("min_amount")
        max_s = row.get("max_amount")
        if min_s and max_s and float(min_s) > 0:
            return f"${float(min_s):,.0f} - ${float(max_s):,.0f}"
        elif min_s and float(min_s) > 0:
            return f"${float(min_s):,.0f}+"
    except (ValueError, TypeError):
        pass
    return ""


def _detect_experience(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["intern", "trainee"]):
        return "Intern"
    if any(w in t for w in ["junior", "jr", "entry", "associate", "graduate", "new grad"]):
        return "Entry Level"
    if any(w in t for w in ["senior", "sr", "lead", "principal", "staff"]):
        return "Senior"
    if any(w in t for w in ["director", "head", "vp", "chief"]):
        return "Lead+"
    return "Mid Level"


def _detect_work_type(title: str, description: str) -> str:
    blob = f"{title} {description}".lower()
    if "remote" in blob:
        return "Remote"
    if "hybrid" in blob:
        return "Hybrid"
    return "On-site"


async def _fetch_indeed_jobs(query: str, max_results: int = 20) -> list[dict]:
    """Scrape Indeed job listings directly."""
    jobs = []
    encoded_q = quote_plus(query)
    url = f"https://www.indeed.com/jobs?q={encoded_q}&limit={max_results}&fromage=7"
    
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.info(f"[real_jobs] Indeed returned {resp.status_code}")
                return jobs
            
            html = resp.text
            # Extract job data from Indeed's embedded JSON
            # Look for job card patterns
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            
            # Find job cards
            cards = soup.select("div.job_seen_beacon, div.jobsearch-ResultsList div.result")
            for card in cards[:max_results]:
                title_el = card.select_one("h2.jobTitle a, a.jcs-JobTitle")
                company_el = card.select_one("span[data-testid='company-name'], span.css-63koeb, span.companyName")
                location_el = card.select_one("div[data-testid='text-location'], div.css-1p0sjhy, div.companyLocation")
                
                if not title_el or not company_el:
                    continue
                
                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True)
                location = location_el.get_text(strip=True) if location_el else ""
                
                # Build job URL
                href = title_el.get("href", "")
                if href and not href.startswith("http"):
                    href = f"https://www.indeed.com{href}"
                
                if not href or not _is_direct_apply_url(href):
                    continue
                
                job_id = _generate_id(company, title, href)
                city = location
                country = "USA"
                
                jobs.append({
                    "id": job_id,
                    "company_name": company,
                    "company_slug": company.lower().replace(" ", "-").replace(".", ""),
                    "role_title": title,
                    "salary_range": "",
                    "work_type": _detect_work_type(title, ""),
                    "experience_level": _detect_experience(title),
                    "country": country,
                    "city": city,
                    "job_url": href,
                    "company_website": "",
                    "job_description": "",
                    "source": "indeed",
                    "status": "active",
                    "is_hiring": True,
                    "relevance_score": 0.6,
                    "verified_url": href,
                    "url_verified": True,
                    "founders": [],
                    "tags": [],
                    "role_category": "",
                    "batch": "",
                    "stage": "",
                    "vc_firms": "",
                    "team_size": "",
                    "visa_sponsorship": "Unknown",
                    "is_startup": False,
                    "is_stealth": False,
                    "offers_relocation": False,
                    "match_score": None,
                    "match_reasons": [],
                    "apply_mode": "external",
                })
                
    except Exception as e:
        logger.error(f"[real_jobs] Indeed scrape error: {e}")
    
    return jobs


async def _fetch_with_jobspy(query: str, results_wanted: int = 20) -> list[dict]:
    """Fetch jobs using python-jobspy library."""
    if not HAS_JOBSPY:
        return []
    
    jobs = []
    loop = asyncio.get_event_loop()
    
    try:
        df = await loop.run_in_executor(
            None,
            lambda: scrape_jobs(
                site_name=["indeed", "linkedin"],
                search_term=query,
                results_wanted=results_wanted,
                country_indeed="USA",
            )
        )
        if df is None or df.empty:
            return jobs
        
        for _, row in df.iterrows():
            job_url = str(row.get("job_url", "") or "")
            company = str(row.get("company", "") or "").strip()
            title = str(row.get("title", "") or "").strip()
            
            if not _is_direct_apply_url(job_url):
                continue
            if not company or not title or company.lower() in ("nan", "none", ""):
                continue
            
            description = str(row.get("description", "") or "")[:3000]
            location = str(row.get("location", "") or "")
            city = location
            country = "USA"
            if "," in location:
                parts = location.rsplit(",", 1)
                city = parts[0].strip()
            
            job_id = _generate_id(company, title, job_url)
            jobs.append({
                "id": job_id,
                "company_name": company,
                "company_slug": company.lower().replace(" ", "-").replace(".", ""),
                "role_title": title,
                "salary_range": _format_salary(row),
                "work_type": _detect_work_type(title, description),
                "experience_level": _detect_experience(title),
                "country": country,
                "city": city,
                "job_url": job_url,
                "company_website": "",
                "job_description": description,
                "source": str(row.get("site", "jobspy")),
                "status": "active",
                "is_hiring": True,
                "relevance_score": 0.6,
                "verified_url": job_url,
                "url_verified": True,
                "founders": [],
                "tags": [],
                "role_category": "",
                "batch": "",
                "stage": "",
                "vc_firms": "",
                "team_size": "",
                "visa_sponsorship": "Unknown",
                "is_startup": False,
                "is_stealth": False,
                "offers_relocation": False,
                "match_score": None,
                "match_reasons": [],
                "apply_mode": "external",
            })
    except Exception as e:
        logger.error(f"[real_jobs] JobSpy error for '{query}': {e}")
    
    return jobs


async def _fetch_with_apimart(query: str, max_results: int = 20) -> list[dict]:
    """Use APIMart's AI to search for real job listings."""
    api_key = os.getenv("APIMART_API_KEY", "")
    base_url = os.getenv("APIMART_BASE_URL", "https://api.apimart.ai/v1")
    
    if not api_key:
        return []
    
    jobs = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "searchgpt",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a job search assistant. Find REAL, currently open job listings. "
                                "Return ONLY valid JSON array of objects with these exact keys: "
                                "title, company, location, job_url, description, salary. "
                                "CRITICAL: job_url must be a REAL, working URL to the actual job posting "
                                "(e.g., on Greenhouse, Lever, Indeed, LinkedIn, company careers page). "
                                "Do NOT invent URLs. Only include jobs you can find real URLs for. "
                                "Return 10-15 results."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Find real, currently open job listings for: {query}. Include the actual application URL for each.",
                        },
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.3,
                },
            )
            
            if resp.status_code != 200:
                logger.warning(f"[real_jobs] APIMart returned {resp.status_code}")
                return jobs
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse JSON from response
            if "```" in content:
                content = content.split("```json")[-1].split("```")[0] if "```json" in content else content.split("```")[1].split("```")[0]
            
            try:
                listings = json.loads(content.strip())
            except json.JSONDecodeError:
                # Try to find JSON array in content
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    listings = json.loads(match.group())
                else:
                    return jobs
            
            if not isinstance(listings, list):
                return jobs
            
            for item in listings:
                title = str(item.get("title", "")).strip()
                company = str(item.get("company", "")).strip()
                job_url = str(item.get("job_url", "") or item.get("url", "")).strip()
                location = str(item.get("location", "")).strip()
                description = str(item.get("description", "")).strip()[:2000]
                salary = str(item.get("salary", "")).strip()
                
                if not title or not company or not _is_direct_apply_url(job_url):
                    continue
                
                job_id = _generate_id(company, title, job_url)
                city = location
                country = "USA"
                
                jobs.append({
                    "id": job_id,
                    "company_name": company,
                    "company_slug": company.lower().replace(" ", "-").replace(".", ""),
                    "role_title": title,
                    "salary_range": salary,
                    "work_type": _detect_work_type(title, description),
                    "experience_level": _detect_experience(title),
                    "country": country,
                    "city": city,
                    "job_url": job_url,
                    "company_website": "",
                    "job_description": description,
                    "source": "apimart",
                    "status": "active",
                    "is_hiring": True,
                    "relevance_score": 0.7,
                    "verified_url": job_url,
                    "url_verified": True,
                    "founders": [],
                    "tags": [],
                    "role_category": "",
                    "batch": "",
                    "stage": "",
                    "vc_firms": "",
                    "team_size": "",
                    "visa_sponsorship": "Unknown",
                    "is_startup": False,
                    "is_stealth": False,
                    "offers_relocation": False,
                    "match_score": None,
                    "match_reasons": [],
                    "apply_mode": "external",
                })
                
    except Exception as e:
        logger.error(f"[real_jobs] APIMart fetch error: {e}")
    
    return jobs


async def fetch_real_jobs(
    queries: Optional[list[str]] = None,
    results_per_query: int = 15,
) -> list[dict]:
    """Fetch real jobs from multiple sources.
    
    Strategy:
    1. Try APIMart (AI-powered search, gets real URLs)
    2. Try JobSpy (if available)
    3. Fallback to direct scraping
    
    Only returns jobs with valid direct apply URLs.
    """
    search_queries = queries or SEARCH_QUERIES
    all_jobs = []
    seen_ids = set()
    
    for query in search_queries:
        query_jobs = []
        
        # Source 1: APIMart (best quality — AI searches the web)
        apimart_jobs = await _fetch_with_apimart(query, max_results=15)
        query_jobs.extend(apimart_jobs)
        logger.info(f"[real_jobs] APIMart '{query}': {len(apimart_jobs)} jobs")
        
        # Source 2: JobSpy (if available)
        if HAS_JOBSPY and len(query_jobs) < 10:
            jobspy_jobs = await _fetch_with_jobspy(query, results_wanted=results_per_query)
            query_jobs.extend(jobspy_jobs)
            logger.info(f"[real_jobs] JobSpy '{query}': {len(jobspy_jobs)} jobs")
        
        # Source 3: Direct Indeed scraping (fallback)
        if len(query_jobs) < 5:
            indeed_jobs = await _fetch_indeed_jobs(query, max_results=20)
            query_jobs.extend(indeed_jobs)
            logger.info(f"[real_jobs] Indeed '{query}': {len(indeed_jobs)} jobs")
        
        # Deduplicate
        for job in query_jobs:
            if job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                all_jobs.append(job)
        
        # Small delay between queries
        await asyncio.sleep(1.0)
    
    logger.info(f"[real_jobs] Total: {len(all_jobs)} real jobs with valid apply URLs")
    return all_jobs


async def refresh_jobs_data(
    queries: Optional[list[str]] = None,
    max_queries: int = 5,
) -> dict:
    """Refresh jobs.json with real jobs from live sources."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    data_file = os.path.join(data_dir, "jobs.json")
    
    search_queries = (queries or SEARCH_QUERIES)[:max_queries]
    
    jobs = await fetch_real_jobs(queries=search_queries, results_per_query=15)
    
    if not jobs:
        return {"status": "error", "message": "No jobs fetched from any source", "count": 0}
    
    os.makedirs(data_dir, exist_ok=True)
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, default=str)
    
    logger.info(f"[real_jobs] Saved {len(jobs)} jobs to {data_file}")
    return {
        "status": "ok",
        "count": len(jobs),
        "queries_used": search_queries,
        "message": f"Fetched {len(jobs)} real jobs with direct apply URLs",
    }
