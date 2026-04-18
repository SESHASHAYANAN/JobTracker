"""
WebSocket routes for real-time browser automation streaming and auto-apply events.
Uses FastAPI WebSocket support with Chrome DevTools Protocol integration.
"""
from __future__ import annotations
import asyncio
import json
import time
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

ws_router = APIRouter()

# ── Active sessions registry ──────────────────────────────────
_active_sessions: dict[str, dict] = {}
_auto_apply_clients: list[WebSocket] = []
_browser_stream_clients: dict[str, list[WebSocket]] = {}


async def broadcast_auto_apply_event(event: dict):
    """Broadcast an auto-apply event to all connected dashboard clients."""
    disconnected = []
    for ws in _auto_apply_clients:
        try:
            await ws.send_json(event)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _auto_apply_clients.remove(ws)


async def broadcast_browser_frame(session_id: str, frame_data: bytes):
    """Broadcast a browser frame to all connected viewer clients."""
    clients = _browser_stream_clients.get(session_id, [])
    disconnected = []
    for ws in clients:
        try:
            await ws.send_bytes(frame_data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        clients.remove(ws)


# ── Auto-Apply Dashboard WebSocket ────────────────────────────
@ws_router.websocket("/ws/auto-apply")
async def ws_auto_apply(ws: WebSocket):
    """
    WebSocket endpoint for the Auto-Apply Dashboard.
    Sends real-time updates about:
    - Queue changes
    - Session status updates
    - Step additions
    - Application completions/failures
    - Intervention requests
    """
    await ws.accept()
    _auto_apply_clients.append(ws)
    logger.info("[ws] Auto-apply dashboard client connected")

    try:
        # Send initial state
        await ws.send_json({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": len(_active_sessions),
        })

        while True:
            # Listen for control messages from the dashboard
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "take_control":
                    session_id = msg.get("sessionId", "")
                    session = _active_sessions.get(session_id)
                    if session:
                        session["status"] = "user_control"
                        await broadcast_auto_apply_event({
                            "type": "session_update",
                            "session": session,
                        })
                    logger.info(f"[ws] User took control of session {session_id}")

                elif msg_type == "resume_automation":
                    session_id = msg.get("sessionId", "")
                    session = _active_sessions.get(session_id)
                    if session:
                        session["status"] = "running"
                        await broadcast_auto_apply_event({
                            "type": "session_update",
                            "session": session,
                        })
                    logger.info(f"[ws] Automation resumed for session {session_id}")

                elif msg_type == "mark_submitted":
                    session_id = msg.get("sessionId", "")
                    session = _active_sessions.get(session_id)
                    if session:
                        session["status"] = "completed"
                        await broadcast_auto_apply_event({
                            "type": "application_complete",
                            "evidence": _build_evidence(session),
                        })
                    logger.info(f"[ws] Session {session_id} marked as submitted by user")

                elif msg_type == "stop_all":
                    for sid, session in _active_sessions.items():
                        session["status"] = "stopped"
                    await broadcast_auto_apply_event({
                        "type": "all_stopped",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    logger.info("[ws] All sessions stopped by user")

                elif msg_type == "remove_job":
                    job_id = msg.get("jobId", "")
                    logger.info(f"[ws] Job {job_id} removed from queue by user")
                    await broadcast_auto_apply_event({
                        "type": "job_removed",
                        "jobId": job_id,
                    })

                elif msg_type == "ping":
                    await ws.send_json({"type": "pong"})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info("[ws] Auto-apply dashboard client disconnected")
    except Exception as e:
        logger.error(f"[ws] Auto-apply WS error: {e}")
    finally:
        if ws in _auto_apply_clients:
            _auto_apply_clients.remove(ws)


# ── Browser Stream WebSocket ─────────────────────────────────
@ws_router.websocket("/ws/browser-stream/{session_id}")
async def ws_browser_stream(ws: WebSocket, session_id: str):
    """
    WebSocket endpoint for streaming browser viewport frames.
    Sends:
    - Binary JPEG/WebP frames for the canvas
    - JSON control messages (click events, highlight events, mouse position)
    """
    await ws.accept()

    if session_id not in _browser_stream_clients:
        _browser_stream_clients[session_id] = []
    _browser_stream_clients[session_id].append(ws)
    logger.info(f"[ws] Browser stream client connected for session {session_id}")

    try:
        # If we have an active session with screenshots, send the latest
        session = _active_sessions.get(session_id)
        if session and session.get("screenshotDataUrl"):
            await ws.send_json({
                "type": "initial_frame",
                "screenshot": session["screenshotDataUrl"],
            })

        while True:
            # Listen for user input events (for user takeover mode)
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "user_input":
                    # Forward user input to the browser automation engine
                    session = _active_sessions.get(session_id)
                    if session and session.get("status") == "user_control":
                        # In a real implementation, this would forward to Playwright/CDP
                        logger.info(f"[ws] User input received: {msg.get('action')}")

                elif msg_type == "ping":
                    await ws.send_json({"type": "pong"})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"[ws] Browser stream client disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"[ws] Browser stream WS error: {e}")
    finally:
        clients = _browser_stream_clients.get(session_id, [])
        if ws in clients:
            clients.remove(ws)
        if not clients and session_id in _browser_stream_clients:
            del _browser_stream_clients[session_id]


# ── Helper functions ──────────────────────────────────────────

def _build_evidence(session: dict) -> dict:
    """Build evidence record from a completed session."""
    return {
        "id": session.get("sessionId", ""),
        "companyName": session.get("companyName", ""),
        "roleTitle": session.get("roleTitle", ""),
        "careersUrl": session.get("currentUrl", ""),
        "confirmationText": session.get("confirmationText"),
        "confirmationNumber": session.get("confirmationNumber"),
        "screenshotUrl": session.get("screenshotDataUrl"),
        "stepLog": session.get("steps", []),
        "submittedAt": datetime.utcnow().isoformat(),
        "emailStatus": "pending",
        "totalTime": session.get("elapsedMs", 0),
        "userIntervened": session.get("userIntervened", False),
        "interventionStep": session.get("interventionStep"),
    }


# ── Session management API functions (called by automation engine) ──

def create_session(session_id: str, job_data: dict) -> dict:
    """Create a new automation session."""
    session = {
        "sessionId": session_id,
        "jobId": job_data.get("id", ""),
        "companyName": job_data.get("company_name", ""),
        "roleTitle": job_data.get("role_title", ""),
        "currentUrl": job_data.get("job_url", ""),
        "pageTitle": "",
        "favicon": "",
        "status": "connecting",
        "steps": [],
        "elapsedMs": 0,
        "mouseX": 0,
        "mouseY": 0,
        "progress": {"current": 0, "total": 0},
        "screenshotDataUrl": None,
        "startTime": time.time(),
        "userIntervened": False,
        "confirmationText": None,
        "confirmationNumber": None,
    }
    _active_sessions[session_id] = session
    return session


def update_session(session_id: str, updates: dict) -> Optional[dict]:
    """Update an active session."""
    session = _active_sessions.get(session_id)
    if session:
        session.update(updates)
        if session.get("startTime"):
            session["elapsedMs"] = int((time.time() - session["startTime"]) * 1000)
    return session


def add_session_step(session_id: str, step: dict) -> Optional[dict]:
    """Add a step to the session log."""
    session = _active_sessions.get(session_id)
    if session:
        # Deactivate previous steps
        for s in session["steps"]:
            s["isActive"] = False
        step["isActive"] = True
        step["stepNumber"] = len(session["steps"]) + 1
        elapsed = time.time() - session.get("startTime", time.time())
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        ms = int((elapsed % 1) * 1000)
        step["timestamp"] = f"{mins:02d}:{secs:02d}.{ms:03d}"
        session["steps"].append(step)
    return session


def end_session(session_id: str, status: str = "completed") -> Optional[dict]:
    """End a session and clean up."""
    session = _active_sessions.get(session_id)
    if session:
        session["status"] = status
        if session.get("startTime"):
            session["elapsedMs"] = int((time.time() - session["startTime"]) * 1000)
    return session


def get_active_sessions() -> dict:
    """Get all active sessions."""
    return _active_sessions
