"""Anti-block HTTP client — user-agent rotation, delays, retries, domain concurrency."""
from __future__ import annotations
import asyncio, random, time
from typing import Optional
import httpx
from fake_useragent import UserAgent

_ua = UserAgent()
_domain_semaphores: dict[str, asyncio.Semaphore] = {}
_MAX_CONCURRENT_PER_DOMAIN = 2


def _sem(domain: str) -> asyncio.Semaphore:
    if domain not in _domain_semaphores:
        _domain_semaphores[domain] = asyncio.Semaphore(_MAX_CONCURRENT_PER_DOMAIN)
    return _domain_semaphores[domain]


def _extract_domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc


async def safe_get(
    url: str,
    headers: Optional[dict] = None,
    timeout: float = 30,
    retries: int = 3,
    json_response: bool = False,
):
    domain = _extract_domain(url)
    sem = _sem(domain)
    h = headers or {}
    h.setdefault("User-Agent", _ua.random)
    h.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    h.setdefault("Accept-Language", "en-US,en;q=0.9")

    for attempt in range(retries):
        async with sem:
            await asyncio.sleep(random.uniform(1.0, 3.0))
            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    resp = await client.get(url, headers=h)
                    resp.raise_for_status()
                    return resp.json() if json_response else resp.text
            except Exception as e:
                if attempt < retries - 1:
                    wait = (2 ** (attempt + 1)) + random.uniform(0, 1)
                    await asyncio.sleep(wait)
                else:
                    print(f"[antiblock] Failed {url} after {retries} retries: {e}")
                    return None


async def safe_post(
    url: str,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: float = 30,
):
    h = headers or {}
    h.setdefault("User-Agent", _ua.random)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.post(url, json=json_body, headers=h)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"[antiblock] POST failed {url}: {e}")
        return None
