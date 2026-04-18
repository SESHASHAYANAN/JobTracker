"""FastAPI main entry point — starts server and kicks off agent coordinator on startup."""
from __future__ import annotations
import asyncio, sys, os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Ensure backend dir is first on sys.path so `agents` resolves to backend/agents, not root agents/
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from routes import router
from agent_routes import agent_router
from ws_routes import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inject startup seed data and run classifier on startup, then kick off coordinator."""
    # ── Immediate: classify all existing jobs ──
    try:
        from store import store
        from services.startup_classifier import classify_and_enrich, compute_startup_rank
        # Classify ALL jobs (existing + new)
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

    # ── Background: run full agent coordinator ──
    print("[main] Starting agent coordinator in background...")
    try:
        from coordinator import run_all_agents
        task = asyncio.create_task(run_all_agents())
    except Exception as e:
        print(f"[main] Coordinator import failed (non-fatal): {e}")
        task = None
    yield
    if task:
        task.cancel()


app = FastAPI(
    title="Startup Job Intelligence API",
    version="1.0.0",
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
    return {"message": "Startup Job Intelligence API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
