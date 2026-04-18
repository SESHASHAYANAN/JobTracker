"""In-memory job store with JSON persistence and server-side filtering."""
from __future__ import annotations
import json, os, threading
from typing import Optional
from datetime import datetime
from models import Job, ApplicationProfile, ApplicationRecord, AutoApplyConfig, DashboardStats

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "jobs.json")


class JobStore:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self.last_crawl: Optional[str] = None
        self.agents_completed: list[str] = []
        # ── In-memory application state ──
        self._application_profile: Optional[ApplicationProfile] = None
        self._applications: dict[str, ApplicationRecord] = {}
        self._auto_apply_config: AutoApplyConfig = AutoApplyConfig()
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
        # ── New startup filters ──
        startup_only: bool = False,
        stealth_only: bool = False,
        engineering_only: bool = False,
        india_only: bool = False,
        founding_only: bool = False,
        min_match_score: Optional[float] = None,
        apply_mode_filter: Optional[str] = None,
        offers_relocation: bool = False,
        remote_india: bool = False,
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
                blob = f"{job.company_name} {job.role_title} {job.country} {job.city} {' '.join(job.startup_tags)} {' '.join(job.industry_tags)}".lower()
                if s not in blob:
                    continue
            # ── NEW: Startup / Stealth / Engineering filters ──
            if startup_only and not job.is_startup:
                continue
            if stealth_only and not job.is_stealth:
                continue
            if engineering_only:
                from services.startup_classifier import is_engineering_role
                if not is_engineering_role(job):
                    continue
            if india_only:
                from services.startup_classifier import is_india_based
                if not is_india_based(job):
                    continue
            if founding_only:
                if "founding" not in (job.role_title or "").lower():
                    continue
            if min_match_score is not None and (job.match_score or 0) < min_match_score:
                continue
            if apply_mode_filter and job.apply_mode != apply_mode_filter:
                continue
            if offers_relocation and not job.offers_relocation:
                continue
            if remote_india:
                w = (job.work_type or "").lower()
                c = (job.country or "").lower()
                if not (w == "remote" and c in ("india", "")):
                    if not any("remote india" in t.lower() for t in job.startup_tags):
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

    # ── Application Profile ──────────────────────────────────

    def save_profile(self, profile: ApplicationProfile):
        self._application_profile = profile

    def get_profile(self) -> Optional[ApplicationProfile]:
        return self._application_profile

    # ── Application Records ──────────────────────────────────

    def add_application(self, record: ApplicationRecord) -> ApplicationRecord:
        if not record.id:
            record.generate_id()
        self._applications[record.id] = record
        return record

    def get_applications(self, status: Optional[str] = None) -> list[ApplicationRecord]:
        apps = list(self._applications.values())
        if status:
            apps = [a for a in apps if a.status.lower() == status.lower()]
        apps.sort(key=lambda a: a.applied_at, reverse=True)
        return apps

    def get_application_by_id(self, app_id: str) -> Optional[ApplicationRecord]:
        return self._applications.get(app_id)

    def update_application(self, app_id: str, **kwargs) -> Optional[ApplicationRecord]:
        record = self._applications.get(app_id)
        if not record:
            return None
        for key, val in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, val)
        return record

    # ── Auto-Apply Config ────────────────────────────────────

    def save_auto_apply_config(self, config: AutoApplyConfig):
        self._auto_apply_config = config

    def get_auto_apply_config(self) -> AutoApplyConfig:
        return self._auto_apply_config

    # ── Dashboard Stats ──────────────────────────────────────

    def get_dashboard_stats(self) -> DashboardStats:
        all_jobs = [j for j in self._jobs.values() if j.is_hiring and j.status == "active"]
        total = len(all_jobs)
        startup_jobs = [j for j in all_jobs if j.is_startup]
        stealth_jobs = [j for j in all_jobs if j.is_stealth]
        india_jobs = []
        for j in all_jobs:
            c = (j.country or "").lower()
            ct = (j.city or "").lower()
            if c == "india" or "india" in ct:
                india_jobs.append(j)
        engineering_jobs = []
        try:
            from services.startup_classifier import is_engineering_role
            engineering_jobs = [j for j in all_jobs if is_engineering_role(j)]
        except Exception:
            pass
        relocation_jobs = [j for j in all_jobs if j.offers_relocation]
        auto_eligible = [j for j in all_jobs if j.apply_mode in ("auto_apply", "one_click")]
        apps = list(self._applications.values())
        applied = [a for a in apps if a.status == "Applied"]
        pending = [a for a in apps if a.status in ("Pending", "Needs Review")]
        failed = [a for a in apps if a.status == "Failed"]
        emails = [a for a in apps if a.email_sent]

        # Tech stack distribution
        tech_counts: dict[str, int] = {}
        for j in startup_jobs:
            for tag in j.industry_tags + j.startup_tags:
                if tag not in ("Startup", "India", "Stealth", "Early Team"):
                    tech_counts[tag] = tech_counts.get(tag, 0) + 1
        top_tech = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_tech_dicts = [{"name": k, "count": v} for k, v in top_tech]

        # Domain distribution
        domain_counts: dict[str, int] = {}
        for j in startup_jobs:
            for tag in j.industry_tags:
                domain_counts[tag] = domain_counts.get(tag, 0) + 1
        top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_domain_dicts = [{"name": k, "count": v} for k, v in top_domains]

        return DashboardStats(
            total_jobs=total,
            total_startup_jobs=len(startup_jobs),
            startup_percentage=round(len(startup_jobs) / max(total, 1) * 100, 1),
            india_jobs=len(india_jobs),
            engineering_jobs=len(engineering_jobs),
            auto_apply_eligible=len(auto_eligible),
            applications_sent=len(applied),
            pending_approvals=len(pending),
            failed_applications=len(failed),
            emails_sent=len(emails),
            top_tech_stacks=top_tech_dicts,
            top_startup_domains=top_domain_dicts,
            stealth_jobs=len(stealth_jobs),
            relocation_jobs=len(relocation_jobs),
        )


store = JobStore()
