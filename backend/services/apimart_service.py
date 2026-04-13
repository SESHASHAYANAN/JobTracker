"""apimart GPT-4o enrichment service."""
from __future__ import annotations
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
_client = OpenAI(
    api_key=os.getenv("APIMART_API_KEY", ""),
    base_url=os.getenv("APIMART_BASE_URL", "https://api.apimart.ai/v1"),
)

# simple in-memory cache to avoid re-enriching
_cache: dict[str, dict] = {}


async def enrich_company(company_name: str, html_snippet: str = "") -> dict:
    """Use GPT-4o via apimart to infer missing company metadata."""
    cache_key = company_name.lower().strip()
    if cache_key in _cache:
        return _cache[cache_key]
    try:
        prompt = (
            "Given this company information, return a JSON object with inferred fields:\n"
            '{"industry_tags": [], "stage": "Seed/A/B/Growth/Unknown", '
            '"team_size_bucket": "1-10/10-50/50-200/200+/Unknown", '
            '"role_category": "AI/ML/Engineering/Design/GTM/Data/Ops/Other", '
            '"founded_year": null, "work_type": "remote/onsite/hybrid/Unknown"}\n\n'
            f"Company: {company_name}\n"
            f"Context:\n{html_snippet[:2000]}"
        )
        resp = _client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(text)
        _cache[cache_key] = data
        return data
    except Exception as e:
        print(f"[apimart] enrich error for {company_name}: {e}")
        return {}
