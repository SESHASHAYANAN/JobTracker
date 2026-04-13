"""Gemini client — long-context CV/JD analysis and section rewriting.

Uses gemini-2.0-flash with rate limiting and retry logic.
Optimized for 10K+ token inputs (full CV + full JD in context).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from agents.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_RPM_LIMIT, GEMINI_MAX_TOKENS


class _GeminiRateLimiter:
    """Simple rate limiter for Gemini API calls."""

    def __init__(self, rpm: int):
        self._interval = 60.0 / rpm
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)
            self._last_call = time.monotonic()


class GeminiClient:
    """Gemini client for long-context CV/JD analysis.

    Used for:
    - Full CV vs JD comparison (10K+ tokens input)
    - Section-by-section CV rewriting (entire CV in context)
    - Gap analysis with mitigation strategies
    - Comp research synthesis

    Model: gemini-2.0-flash (up to 1M token context window)
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        genai.configure(api_key=api_key or GEMINI_API_KEY)
        self._model = genai.GenerativeModel(model or GEMINI_MODEL)
        self._rate_limiter = _GeminiRateLimiter(GEMINI_RPM_LIMIT)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def _call(self, prompt: str, max_tokens: int = GEMINI_MAX_TOKENS) -> str:
        """Make a rate-limited call to Gemini."""
        await self._rate_limiter.acquire()
        try:
            resp = self._model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.3,
                ),
            )
            return resp.text.strip() if resp.text else ""
        except Exception as e:
            print(f"[gemini] API error: {e}")
            raise

    async def analyze(self, prompt: str, max_tokens: int = GEMINI_MAX_TOKENS) -> str:
        """Generate analysis text from a prompt."""
        return await self._call(prompt, max_tokens)

    async def analyze_structured(self, prompt: str, max_tokens: int = GEMINI_MAX_TOKENS) -> dict:
        """Generate structured JSON analysis."""
        full_prompt = (
            f"{prompt}\n\n"
            "Respond with ONLY valid JSON. No markdown fences, no commentary."
        )
        raw = await self._call(full_prompt, max_tokens)
        # Strip markdown fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass
            return {}

    async def compare_cv_jd(self, cv_text: str, jd_text: str) -> dict:
        """Deep comparison of CV against JD with structured output.

        Returns dict with keys:
        - match_summary: str — overall match assessment
        - matched_requirements: list[dict] — requirement → CV evidence
        - gaps: list[dict] — gap → severity → mitigation
        - strengths: list[str] — candidate's unique advantages
        - keywords_found: list[str] — JD keywords present in CV
        - keywords_missing: list[str] — JD keywords absent from CV
        """
        prompt = (
            "You are an expert career evaluator performing a deep CV-JD comparison.\n\n"
            "--- CANDIDATE CV ---\n"
            f"{cv_text}\n\n"
            "--- JOB DESCRIPTION ---\n"
            f"{jd_text}\n\n"
            "Analyze the fit in detail. Return a JSON object with these keys:\n"
            "1. match_summary (string): 2-3 sentence overall assessment\n"
            "2. matched_requirements (array of objects with 'requirement', 'cv_evidence', 'strength' [1-5])\n"
            "3. gaps (array of objects with 'gap', 'severity' ['critical','moderate','minor'], 'mitigation')\n"
            "4. strengths (array of strings): candidate's unique advantages\n"
            "5. keywords_found (array of strings): JD keywords present in CV\n"
            "6. keywords_missing (array of strings): JD keywords absent from CV\n\n"
            "Be specific — cite exact phrases from both CV and JD."
        )
        return await self.analyze_structured(prompt, max_tokens=4096)

    async def rewrite_section(
        self,
        section_name: str,
        original_text: str,
        keywords: list[str],
        jd_context: str,
        archetype: str = "general",
    ) -> str:
        """Rewrite a CV section for JD-specific tailoring.

        Rules (from career-ops pdf.md):
        - NEVER invent experience — only reformulate with JD vocabulary
        - Inject keywords naturally into existing achievements
        - Maintain same factual content, adapt phrasing
        """
        prompt = (
            "You are an expert ATS-optimized resume writer.\n\n"
            f"Rewrite this '{section_name}' section to better match the target job.\n\n"
            f"Role archetype: {archetype}\n"
            f"Target keywords to inject naturally: {', '.join(keywords[:10])}\n\n"
            f"--- ORIGINAL SECTION ---\n{original_text}\n\n"
            f"--- JOB DESCRIPTION CONTEXT ---\n{jd_context[:2000]}\n\n"
            "CRITICAL RULES:\n"
            "- NEVER add skills or experience the candidate doesn't have\n"
            "- ONLY reformulate existing text using JD vocabulary\n"
            "- Keep the same factual content, adapt phrasing\n"
            "- Use action verbs, quantify where possible\n"
            "- Avoid clichés: 'passionate about', 'proven track record', 'leveraged'\n"
            "- Mix sentence lengths, vary structure\n\n"
            "Return ONLY the rewritten section text, no explanations."
        )
        return await self.analyze(prompt, max_tokens=2048)

    async def generate_gap_analysis(self, cv_text: str, jd_text: str) -> dict:
        """Generate detailed gap analysis with mitigation strategies."""
        prompt = (
            "Analyze the gaps between this candidate's CV and the job requirements.\n\n"
            f"--- CV ---\n{cv_text}\n\n"
            f"--- JD ---\n{jd_text}\n\n"
            "For each gap, provide a JSON object with:\n"
            "1. gap (string): what's missing\n"
            "2. severity (string): 'critical', 'moderate', or 'minor'\n"
            "3. is_blocker (boolean): true if it's a hard requirement\n"
            "4. adjacent_experience (string): related experience the candidate has\n"
            "5. mitigation (string): concrete strategy to address this gap\n"
            "6. cover_letter_phrase (string): how to address in cover letter\n\n"
            "Return a JSON object: {\"gaps\": [array of gap objects]}"
        )
        return await self.analyze_structured(prompt, max_tokens=3000)
