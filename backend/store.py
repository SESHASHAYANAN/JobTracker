"""In-memory job store with JSON persistence and server-side filtering."""
from __future__ import annotations
import json, os, threading
from typing import Optional
from datetime import datetime
from models import Job

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "jobs.json")


class JobStore:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self.last_crawl: Optional[str] = None
        self.agents_completed: list[str] = []
        self._load()

    # ── persistence ──────────────────────────────────────────
    def _load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                skipped = 0
                for i, item in enumerate(raw):
                    try:
                        job = Job(**item)
                        self._jobs[job.id] = job
                    except Exception as e:
                        skipped += 1
                        if skipped <= 5:
                            print(f"[store] WARN Skipped job #{i} ({item.get('company_name', '?')}): {e}")
                if skipped:
                    print(f"[store] WARN Skipped {skipped}/{len(raw)} jobs due to parse errors")
                print(f"[store] OK Loaded {len(self._jobs)} jobs from {DATA_FILE}")
            except Exception as e:
                print(f"[store] ERR Failed to load jobs.json: {e}")

    def _save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([j.model_dump() for j in self._jobs.values()], f, default=str)

    # ── mutations ────────────────────────────────────────────
    def add_jobs(self, jobs: list[Job]):
        with self._lock:
            for job in jobs:
                if not job.id:
                    job.generate_id()
                # dedup: keep highest relevance_score
                existing = self._jobs.get(job.id)
                if existing and existing.relevance_score >= job.relevance_score:
                    continue
                self._jobs[job.id] = job
            self._save()

    def mark_crawl(self, agent_name: str):
        self.last_crawl = datetime.utcnow().isoformat()
        if agent_name not in self.agents_completed:
            self.agents_completed.append(agent_name)

    # ── queries ──────────────────────────────────────────────
    def get_jobs(
        self,
        role: Optional[str] = None,
        visa: Optional[str] = None,
        country: Optional[str] = None,
        stage: Optional[str] = None,
        vc: Optional[str] = None,
        batch: Optional[str] = None,
        level: Optional[str] = None,
        funding_min: Optional[int] = None,
        funding_max: Optional[int] = None,
        team_size_bucket: Optional[str] = None,
        founder_name: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 30,
    ) -> tuple[list[Job], int]:
        results = []
        for job in self._jobs.values():
            # ── ALWAYS exclude inactive / not-hiring ──
            if not job.is_hiring or job.status != "active":
                continue
            if role and role.lower() not in (job.role_category or "").lower() and role.lower() not in (job.role_title or "").lower():
                continue
            if visa and visa.lower() != (job.visa_sponsorship or "").lower():
                continue
            if country and country.lower() != (job.country or "").lower():
                if country.lower() != "remote" or (job.work_type or "").lower() != "remote":
                    continue
            if stage and stage.lower() != (job.stage or "").lower():
                continue
            if vc:
                if not any(vc.lower() in v.lower() for v in job.vc_backers):
                    continue
            if batch and batch.lower() != (job.batch or "").lower():
                continue
            if level and level.lower() != (job.experience_level or "").lower():
                continue
            if team_size_bucket:
                ts = job.team_size or 0
                if team_size_bucket == "1-10" and not (1 <= ts <= 10):
                    continue
                elif team_size_bucket == "10-50" and not (10 <= ts <= 50):
                    continue
                elif team_size_bucket == "50-200" and not (50 <= ts <= 200):
                    continue
                elif team_size_bucket == "200+" and ts < 200:
                    continue
            if founder_name:
                fn_lower = founder_name.lower()
                if not any(fn_lower in f.name.lower() for f in job.founders):
                    continue
            if search:
                s = search.lower()
                blob = f"{job.company_name} {job.role_title} {job.country} {job.city}".lower()
                if s not in blob:
                    continue
            results.append(job)
        # sort by relevance
        results.sort(key=lambda j: j.relevance_score, reverse=True)
        total = len(results)
        start = (page - 1) * limit
        return results[start : start + limit], total

    def get_company(self, slug: str) -> list[Job]:
        return [j for j in self._jobs.values() if j.company_slug == slug and j.is_hiring and j.status == "active"]

    def search_founders(self, query: str) -> list[dict]:
        results = []
        seen = set()
        q = query.lower()
        for job in self._jobs.values():
            for f in job.founders:
                if q in f.name.lower() and f.name not in seen:
                    seen.add(f.name)
                    results.append({**f.model_dump(), "company": job.company_name})
        return results

    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def update_job(self, job: Job):
        with self._lock:
            self._jobs[job.id] = job
            self._save()

    @property
    def count(self) -> int:
        return len([j for j in self._jobs.values() if j.is_hiring and j.status == "active"])


store = JobStore()
