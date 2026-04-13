"""Groq LPU client — fast structured inference for scoring, classification, extraction.

Uses llama-3.3-70b-versatile with rate limiting and retry logic.
Optimized for sub-second responses on structured output tasks.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from agents.config import GROQ_API_KEY, GROQ_MODEL, GROQ_RPM_LIMIT, GROQ_MAX_TOKENS


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, rpm: int):
        self._rpm = rpm
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


class GroqClient:
    """Groq LPU client for fast structured inference.

    Used for:
    - Archetype detection (~200 tokens, ~0.3s)
    - Individual dimension scoring (~300 tokens each, ~0.5s)
    - Keyword extraction from JDs (~150 tokens, ~0.2s)
    - Quick classification tasks

    Rate limit: configurable RPM with token bucket + exponential backoff.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._client = Groq(api_key=api_key or GROQ_API_KEY)
        self._model = model or GROQ_MODEL
        self._rate_limiter = RateLimiter(GROQ_RPM_LIMIT)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def _call(
        self,
        system: str,
        user: str,
        max_tokens: int = GROQ_MAX_TOKENS,
        temperature: float = 0.3,
    ) -> str:
        """Make a rate-limited call to Groq."""
        await self._rate_limiter.acquire()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[groq] API error: {e}")
            raise

    async def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = GROQ_MAX_TOKENS,
        temperature: float = 0.3,
    ) -> str:
        """Generate text with the given system/user prompts."""
        return await self._call(system, user, max_tokens, temperature)

    async def classify(self, text: str, categories: list[str], context: str = "") -> str:
        """Classify text into one of the given categories."""
        system = (
            "You are a precise text classifier. "
            "Respond with ONLY the category name, nothing else. "
            f"Valid categories: {', '.join(categories)}"
        )
        user = f"{context}\n\nText to classify:\n{text[:3000]}" if context else text[:3000]
        result = await self._call(system, user, max_tokens=50, temperature=0.1)
        # Find best match from categories
        result_lower = result.lower().strip()
        for cat in categories:
            if cat.lower() in result_lower:
                return cat
        return categories[0]  # fallback to first category

    async def extract_json(self, prompt: str, system: str = "") -> dict:
        """Extract structured JSON from text. Returns parsed dict."""
        sys_prompt = system or (
            "You are a precise data extraction assistant. "
            "Respond with ONLY valid JSON, no markdown fences, no commentary."
        )
        raw = await self._call(sys_prompt, prompt, max_tokens=GROQ_MAX_TOKENS, temperature=0.1)
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass
            return {}

    async def score_dimension(
        self,
        dimension_name: str,
        dimension_desc: str,
        cv_excerpt: str,
        jd_excerpt: str,
    ) -> dict:
        """Score a single evaluation dimension (1-5) with reasoning."""
        system = (
            "You are an expert career evaluator. Score the candidate-job fit "
            "on the given dimension from 1.0 to 5.0 (use one decimal). "
            "Respond with ONLY valid JSON: "
            '{"score": float, "reasoning": "string", "evidence": ["string"]}'
        )
        user = (
            f"Dimension: {dimension_name}\n"
            f"Description: {dimension_desc}\n\n"
            f"--- CANDIDATE CV (excerpt) ---\n{cv_excerpt[:1500]}\n\n"
            f"--- JOB DESCRIPTION (excerpt) ---\n{jd_excerpt[:1500]}\n\n"
            f"Score this dimension 1.0-5.0 with reasoning and evidence."
        )
        return await self.extract_json(user, system)

    async def extract_keywords(self, jd_text: str, count: int = 20) -> list[str]:
        """Extract ATS keywords from a job description."""
        system = (
            "You extract ATS-critical keywords from job descriptions. "
            "Return ONLY a JSON array of strings, ordered by importance. "
            "Include technical skills, tools, methodologies, and domain terms. "
            f"Extract exactly {count} keywords."
        )
        raw = await self._call(system, jd_text[:3000], max_tokens=500, temperature=0.1)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            result = json.loads(raw)
            if isinstance(result, list):
                return result[:count]
        except json.JSONDecodeError:
            pass
        return []
