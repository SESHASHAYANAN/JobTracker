"""FastAPI main entry point — starts server and kicks off agent coordinator on startup."""
from __future__ import annotations
import asyncio, sys, os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env from project root
_project_root = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(os.path.dirname(_project_root), '.env')
if not os.path.exists(_env_path):
    _env_path = os.path.join(_project_root, '..', '.env')
load_dotenv(_env_path)

# Also try loading from the project root (one level up from backend/)
_parent_env = os.path.join(os.path.dirname(_project_root), '.env')
if os.path.exists(_parent_env):
    load_dotenv(_parent_env, override=True)

# Ensure backend dir is first on sys.path
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from routes import router
from agent_routes import agent_router
from ws_routes import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: check if we need real jobs, then run agents."""
    from store import store

    # ── Check if data is fake seed data ──
    total = len(store._jobs)
    fake_count = sum(1 for j in store._jobs.values() 
                     if j.role_title and j.role_title.startswith("Open Role at"))
    
    if total == 0 or fake_count > total * 0.5:
        print(f"[main] Detected {fake_count}/{total} fake seed jobs. Fetching real jobs...")
        try:
            from services.real_job_fetcher import refresh_jobs_data
            result = await refresh_jobs_data(max_queries=5)
            if result["status"] == "ok":
                store._jobs.clear()
                store._load()
                print(f"[main] OK Loaded {result['count']} real jobs with apply URLs")
            else:
                print(f"[main] WARN Could not fetch real jobs: {result.get('message')}")
        except Exception as e:
            print(f"[main] WARN Real job fetch failed (non-fatal): {e}")
    else:
        print(f"[main] OK {total} jobs loaded ({total - fake_count} real jobs)")

    # ── Classify existing jobs for startup signals ──
    try:
        from services.startup_classifier import classify_and_enrich, compute_startup_rank
        classified = 0
        for job in list(store._jobs.values()):
            try:
                classify_and_enrich(job)
                job.relevance_score = max(job.relevance_score, compute_startup_rank(job))
                classified += 1
            except Exception:
                pass
        store._save()
        print(f"[main] Classified {classified} jobs for startup/stealth signals")
    except Exception as e:
        print(f"[main] Startup classify failed (non-fatal): {e}")

    # ── Background: run agent coordinator ──
    task = None
    try:
        from coordinator import run_all_agents
        task = asyncio.create_task(run_all_agents())
    except Exception as e:
        print(f"[main] Coordinator import failed (non-fatal): {e}")

    # ── Background: verify job URLs (only if we have unverified jobs) ──
    verify_task = None
    unverified = store.get_unverified_jobs(limit=1)
    if unverified and os.getenv("GEMINI_API_KEY") and os.getenv("GROQ_API_KEY"):
        try:
            from services.link_verifier import run_background_verification
            verify_task = asyncio.create_task(run_background_verification(batch_size=20, delay=3.0))
        except Exception as e:
            print(f"[main] Link verifier import failed (non-fatal): {e}")
    else:
        print("[main] Skipping link verification (no unverified jobs or missing API keys)")

    yield
    if task:
        task.cancel()
    if verify_task:
        verify_task.cancel()


app = FastAPI(
    title="Startup Job Intelligence API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(agent_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"message": "Startup Job Intelligence API v2.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
