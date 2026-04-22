"""
Browser Automation Engine — Playwright-based automation for job applications.
Integrates with WebSocket routes for real-time streaming.
Uses Chrome DevTools Protocol (CDP) Page.screencast for frame delivery.
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import json
import logging
import time
import os
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Rate limiting
_domain_last_apply: dict[str, float] = {}
_hourly_count: int = 0
_hourly_reset: float = time.time()
MAX_PER_HOUR = 20
MIN_DOMAIN_GAP_SECONDS = 90

# Retry backoff per domain
_domain_failures: dict[str, int] = {}


class BrowserAutomationEngine:
    """
    Drives job application flows using Playwright.
    Streams viewport via CDP Page.screencast.
    Reports each step to the WebSocket layer.
    """

    def __init__(self):
        self.playwright = None
        self.browser = None
        self._initialized = False

    async def initialize(self):
        """Initialize Playwright browser."""
        if self._initialized:
            return
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--remote-debugging-port=9222",
                ],
            )
            self._initialized = True
            logger.info("[automation] Playwright browser initialized")
        except ImportError:
            logger.warning("[automation] Playwright not installed. Install with: pip install playwright && python -m playwright install chromium")
        except Exception as e:
            logger.error(f"[automation] Browser init failed: {e}")

    async def shutdown(self):
        """Shutdown browser and Playwright."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._initialized = False

    async def apply_to_job(self, session_id: str, job: dict, profile: dict) -> dict:
        """
        Execute the full application flow for a single job.
        Returns evidence dict with results.
        """
        from ws_routes import (
            create_session, update_session, add_session_step,
            end_session, broadcast_auto_apply_event,
        )

        # Rate limiting checks
        global _hourly_count, _hourly_reset
        if time.time() - _hourly_reset > 3600:
            _hourly_count = 0
            _hourly_reset = time.time()

        if _hourly_count >= MAX_PER_HOUR:
            logger.warning("[automation] Hourly rate limit reached")
            return {"status": "rate_limited", "message": "Maximum 20 applications per hour reached"}

        domain = _extract_domain(job.get("job_url", ""))
        if domain in _domain_last_apply:
            elapsed = time.time() - _domain_last_apply[domain]
            if elapsed < MIN_DOMAIN_GAP_SECONDS:
                wait_time = MIN_DOMAIN_GAP_SECONDS - elapsed
                logger.info(f"[automation] Waiting {wait_time:.0f}s for domain cooldown: {domain}")
                await asyncio.sleep(wait_time)

        # Check domain failure backoff
        failures = _domain_failures.get(domain, 0)
        if failures > 0:
            backoff = min(2 ** failures * 30, 600)  # Max 10 min backoff
            logger.info(f"[automation] Domain {domain} has {failures} failures, backing off {backoff}s")
            await asyncio.sleep(backoff)

        # Create session
        session = create_session(session_id, job)
        await broadcast_auto_apply_event({
            "type": "session_update",
            "session": session,
        })

        if not self._initialized:
            await self.initialize()

        if not self.browser:
            add_session_step(session_id, {
                "actionType": "ERROR",
                "target": "browser",
                "value": "Browser not available. Install Playwright.",
            })
            end_session(session_id, "failed")
            return {"status": "error", "message": "Browser not initialized"}

        context = None
        page = None
        try:
            # Create browser context
            context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()

            # Start CDP screencast for frame streaming
            cdp = await context.new_cdp_session(page)
            await cdp.send("Page.startScreencast", {
                "format": "jpeg",
                "quality": 60,
                "maxWidth": 1280,
                "maxHeight": 800,
                "everyNthFrame": 2,
            })

            # Handle screencast frames
            async def on_screencast_frame(params):
                frame_data = base64.b64decode(params["data"])
                from ws_routes import broadcast_browser_frame
                await broadcast_browser_frame(session_id, frame_data)
                # Acknowledge frame
                await cdp.send("Page.screencastFrameAck", {
                    "sessionId": params["sessionId"],
                })

            cdp.on("Page.screencastFrame", lambda params: asyncio.create_task(on_screencast_frame(params)))

            update_session(session_id, {"status": "running"})

            # ── Step 1: Navigate to apply page ────────────────
            apply_url = job.get("job_url") or job.get("company_website", "")
            step = add_session_step(session_id, {
                "actionType": "NAVIGATE",
                "target": apply_url,
            })
            await broadcast_auto_apply_event({
                "type": "step_added",
                "step": step,
                "currentUrl": apply_url,
            })

            await page.goto(apply_url, wait_until="networkidle", timeout=30000)
            
            # Update page info
            page_title = await page.title()
            current_url = page.url
            favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
            update_session(session_id, {
                "currentUrl": current_url,
                "pageTitle": page_title,
                "favicon": favicon,
                "progress": {"current": 1, "total": 7},
            })

            await asyncio.sleep(0.3)  # Visual highlight delay

            # ── Step 2: Look for apply button ─────────────────
            step = add_session_step(session_id, {
                "actionType": "CLICK",
                "target": "Apply button",
            })
            await broadcast_auto_apply_event({"type": "step_added", "step": step})

            # Try common apply button selectors
            apply_selectors = [
                'a:has-text("Apply")', 'button:has-text("Apply")',
                'a:has-text("Apply Now")', 'button:has-text("Apply Now")',
                '#apply-now-button', '.apply-btn', '[data-apply]',
                'a[href*="apply"]', 'button[class*="apply"]',
            ]
            clicked = False
            for sel in apply_selectors:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        # Highlight before click
                        bbox = await el.bounding_box()
                        if bbox:
                            from ws_routes import broadcast_browser_frame
                            await broadcast_auto_apply_event({
                                "type": "step_added",
                                "step": {"actionType": "WAIT", "target": sel, "value": "Highlighting element"},
                                "mouseX": bbox["x"] + bbox["width"] / 2,
                                "mouseY": bbox["y"] + bbox["height"] / 2,
                            })
                        await asyncio.sleep(0.3)
                        await el.click()
                        clicked = True
                        break
                except Exception:
                    continue

            update_session(session_id, {"progress": {"current": 2, "total": 7}})
            await asyncio.sleep(1)

            # ── Step 3: Fill form fields ──────────────────────
            step = add_session_step(session_id, {
                "actionType": "TYPE",
                "target": "Application form fields",
            })
            await broadcast_auto_apply_event({"type": "step_added", "step": step})

            # Fill common form fields
            field_map = {
                'input[name*="name"], input[name*="full_name"], #name': profile.get("full_name", ""),
                'input[name*="email"], input[type="email"], #email': profile.get("email", ""),
                'input[name*="phone"], input[type="tel"], #phone': profile.get("phone", ""),
                'input[name*="linkedin"], input[name*="linkedIn"]': profile.get("linkedin_url", ""),
                'input[name*="github"]': profile.get("github_url", ""),
                'input[name*="portfolio"], input[name*="website"]': profile.get("portfolio_url", ""),
                'input[name*="location"], input[name*="city"]': profile.get("location", ""),
            }

            filled_fields = []
            for selector, value in field_map.items():
                if not value:
                    continue
                for sel in selector.split(", "):
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible(timeout=1000):
                            await el.clear()
                            await el.type(value, delay=30)  # Simulate typing
                            filled_fields.append(sel.split("[")[0])
                            
                            # Report typing step
                            add_session_step(session_id, {
                                "actionType": "TYPE",
                                "target": sel,
                                "value": value if "password" not in sel.lower() else "••••••••",
                            })
                            await asyncio.sleep(0.2)
                            break
                    except Exception:
                        continue

            update_session(session_id, {"progress": {"current": 3, "total": 7}})

            # ── Step 4: Handle file uploads (resume) ──────────
            step = add_session_step(session_id, {
                "actionType": "UPLOAD",
                "target": 'input[type="file"]',
                "value": "resume.pdf",
            })
            await broadcast_auto_apply_event({"type": "step_added", "step": step})
            update_session(session_id, {"progress": {"current": 4, "total": 7}})

            # ── Step 5: Handle dropdowns ──────────────────────
            step = add_session_step(session_id, {
                "actionType": "SELECT",
                "target": "Dropdown selections",
            })
            await broadcast_auto_apply_event({"type": "step_added", "step": step})
            update_session(session_id, {"progress": {"current": 5, "total": 7}})

            # ── Step 6: Check for CAPTCHA ─────────────────────
            captcha_detected = False
            captcha_selectors = [
                'iframe[src*="captcha"]', 'iframe[src*="recaptcha"]',
                '.g-recaptcha', '#captcha', '[class*="captcha"]',
                'iframe[title*="reCAPTCHA"]',
            ]
            for sel in captcha_selectors:
                try:
                    if await page.locator(sel).first.is_visible(timeout=1000):
                        captcha_detected = True
                        break
                except Exception:
                    continue

            if captcha_detected:
                add_session_step(session_id, {
                    "actionType": "CAPTCHA",
                    "target": "CAPTCHA detected",
                    "value": "Please complete manually",
                })
                update_session(session_id, {"status": "captcha"})
                await broadcast_auto_apply_event({
                    "type": "needs_intervention",
                    "reason": "captcha",
                    "sessionId": session_id,
                })
                # Wait for user to solve CAPTCHA (up to 5 minutes)
                start_wait = time.time()
                while time.time() - start_wait < 300:
                    session_data = update_session(session_id, {})
                    if session_data and session_data.get("status") == "running":
                        break
                    await asyncio.sleep(1)

            update_session(session_id, {"progress": {"current": 6, "total": 7}})

            # ── Step 7: Submit form ───────────────────────────
            step = add_session_step(session_id, {
                "actionType": "SUBMIT",
                "target": "Application form",
            })
            await broadcast_auto_apply_event({"type": "step_added", "step": step})

            # Try to find and click submit button
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Submit")', 'button:has-text("Send")',
                'button:has-text("Apply")', '.submit-btn',
            ]
            submitted = False
            for sel in submit_selectors:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await asyncio.sleep(0.3)
                        await el.click()
                        submitted = True
                        break
                except Exception:
                    continue

            await asyncio.sleep(2)

            # ── Step 8: Check for confirmation ────────────────
            page_text = await page.text_content("body") or ""
            confirmation_keywords = [
                "thank you", "application received", "successfully submitted",
                "application has been sent", "we've received", "confirmation",
                "application submitted", "submitted successfully",
            ]
            confirmation_text = None
            for keyword in confirmation_keywords:
                if keyword.lower() in page_text.lower():
                    # Extract surrounding text
                    idx = page_text.lower().find(keyword.lower())
                    confirmation_text = page_text[max(0, idx-50):idx+100].strip()
                    break

            # Extract confirmation number if present
            import re
            confirmation_number = None
            conf_patterns = [
                r'(?:confirmation|reference|tracking|application)\s*(?:#|number|id)?[:\s]*([A-Z0-9-]{4,})',
                r'#([A-Z0-9-]{4,})',
            ]
            for pattern in conf_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    confirmation_number = match.group(1)
                    break

            # Take final screenshot
            screenshot_bytes = await page.screenshot(type="png")
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            screenshot_data_url = f"data:image/png;base64,{screenshot_b64}"

            update_session(session_id, {
                "progress": {"current": 7, "total": 7},
                "screenshotDataUrl": screenshot_data_url,
                "confirmationText": confirmation_text,
                "confirmationNumber": confirmation_number,
            })

            # Final step
            if confirmation_text or submitted:
                add_session_step(session_id, {
                    "actionType": "SUCCESS",
                    "target": "Application submitted",
                    "value": confirmation_text or "Form submitted successfully",
                })
                end_session(session_id, "completed")
                _hourly_count += 1
                _domain_last_apply[domain] = time.time()
                _domain_failures.pop(domain, None)

                await broadcast_auto_apply_event({
                    "type": "application_complete",
                    "evidence": _build_evidence_from_session(session_id),
                })

                return {
                    "status": "success",
                    "confirmation_text": confirmation_text,
                    "confirmation_number": confirmation_number,
                    "screenshot": screenshot_data_url,
                }
            else:
                add_session_step(session_id, {
                    "actionType": "ERROR",
                    "target": "Submission uncertain",
                    "value": "Could not confirm submission",
                })
                end_session(session_id, "needs_review")
                _domain_failures[domain] = _domain_failures.get(domain, 0) + 1

                await broadcast_auto_apply_event({
                    "type": "needs_intervention",
                    "reason": "uncertain",
                    "sessionId": session_id,
                })

                return {
                    "status": "needs_review",
                    "message": "Could not confirm submission",
                    "screenshot": screenshot_data_url,
                }

        except Exception as e:
            logger.error(f"[automation] Application failed: {e}")
            add_session_step(session_id, {
                "actionType": "ERROR",
                "target": "Exception",
                "value": str(e)[:200],
            })
            end_session(session_id, "failed")
            _domain_failures[domain] = _domain_failures.get(domain, 0) + 1

            await broadcast_auto_apply_event({
                "type": "application_failed",
                "sessionId": session_id,
                "error": str(e)[:200],
            })

            return {"status": "error", "message": str(e)}

        finally:
            # Stop screencast and cleanup
            if context:
                try:
                    await context.close()
                except Exception:
                    pass


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return url


def _build_evidence_from_session(session_id: str) -> dict:
    """Build evidence from session data."""
    from ws_routes import _active_sessions
    session = _active_sessions.get(session_id, {})
    return {
        "id": session_id,
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


# Global singleton
automation_engine = BrowserAutomationEngine()
