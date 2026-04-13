"""ScoringAgent — evaluate job-candidate fit using A-F scoring across 10 dimensions.

Split LLM strategy:
  - Groq: archetype detection, individual dimension scoring (fast, ~0.5s each)
  - Gemini: full CV-JD comparison, gap analysis (long-context, ~3s each)
"""
from __future__ import annotations

import asyncio
import re
from typing import Optional

import aiohttp

from agents.config import AUTO_PDF_SCORE, MIN_APPLY_SCORE, REPORTS_DIR
from agents.models import (
    Archetype, DimensionScore, Grade, ScoringResult,
)
from agents.llm.groq_client import GroqClient
from agents.llm.gemini_client import GeminiClient
from agents.scoring.dimensions import DIMENSIONS
from agents.scoring.archetype import detect_archetype
from agents.scoring.report import generate_report


class ScoringAgent:
    """Evaluates job-candidate fit using A-F scoring across 10 dimensions.

    Pipeline (inspired by career-ops oferta.md blocks A-F):
    1. Archetype Detection → classify JD into 6 types (Groq, ~0.3s)
    2. CV-JD Match Analysis → full comparison (Gemini, ~3s)
    3. 10-Dimension Scoring → each scored independently (Groq, ~0.5s each)
    4. Gap Analysis → identify gaps + mitigation (Gemini, ~2s)
    5. Grade Computation → weighted average → A-F letter grade
    6. Report Generation → structured markdown report
    """

    def __init__(self):
        self._groq = GroqClient()
        self._gemini = GeminiClient()

    async def evaluate(
        self,
        jd_text: str,
        cv_text: str,
        url: str = "",
        company: str = "",
        role: str = "",
    ) -> ScoringResult:
        """Evaluate a single job description against a CV.

        Args:
            jd_text: Full job description text.
            cv_text: Full CV/resume text.
            url: Job URL (for reference).
            company: Company name.
            role: Role title.

        Returns:
            ScoringResult with scores, grade, and report path.
        """
        if not company or not role:
            # Try to extract from JD
            info = await self._extract_job_info(jd_text)
            company = company or info.get("company", "Unknown")
            role = role or info.get("role", "Unknown Role")

        print(f"  [scoring] Evaluating: {company} - {role}")

        # 1. Archetype Detection (Groq — fast)
        print("  [scoring] Step 1/5: Detecting archetype...")
        archetype, confidence = await detect_archetype(jd_text, self._groq)

        # 2. CV-JD Match Analysis (Gemini — long-context)
        print("  [scoring] Step 2/5: Analyzing CV-JD match...")
        match_analysis = await self._gemini.compare_cv_jd(cv_text, jd_text)

        # 3. Score all 10 dimensions in parallel (Groq — fast)
        print("  [scoring] Step 3/5: Scoring 10 dimensions...")
        dimension_scores = await self._score_all_dimensions(cv_text, jd_text)

        # 4. Gap Analysis (Gemini — long-context)
        print("  [scoring] Step 4/5: Analyzing gaps...")
        gap_data = await self._gemini.generate_gap_analysis(cv_text, jd_text)

        # 5. Build result
        result = ScoringResult(
            company=company,
            role=role,
            url=url,
            archetype=archetype,
            archetype_confidence=confidence,
            dimensions=dimension_scores,
            cv_match_summary=match_analysis.get("match_summary", ""),
            gaps=[g.get("gap", "") for g in gap_data.get("gaps", [])],
            gap_mitigations=[g.get("mitigation", "") for g in gap_data.get("gaps", [])],
            keywords=match_analysis.get("keywords_found", []) + match_analysis.get("keywords_missing", []),
        )

        # Compute weighted average and grade
        result.overall_score = result.compute_overall()
        result.grade = result.compute_grade()

        # Set recommendation
        result.recommendation = self._get_recommendation(result.overall_score, result.grade)

        # 6. Generate and save report
        print("  [scoring] Step 5/5: Generating report...")
        report_path = self._save_report(result, match_analysis, gap_data)
        result.report_path = str(report_path)

        print(f"  [scoring] [OK] Score: {result.overall_score}/5.0 ({result.grade.value}) - {result.recommendation}")
        return result

    async def evaluate_url(
        self,
        url: str,
        cv_text: str,
    ) -> ScoringResult:
        """Evaluate a job from a URL by fetching the JD first."""
        print(f"  [scoring] Fetching JD from: {url}")
        jd_text = await self._fetch_jd(url)
        if not jd_text:
            return ScoringResult(
                company="Unknown",
                role="Unknown",
                url=url,
                overall_score=0.0,
                grade=Grade.F,
                recommendation="Could not fetch job description from URL.",
            )
        return await self.evaluate(jd_text, cv_text, url=url)

    async def compare(self, results: list[ScoringResult]) -> str:
        """Generate a comparison report across multiple scored jobs."""
        if not results:
            return "No results to compare."

        # Sort by score descending
        sorted_results = sorted(results, key=lambda r: r.overall_score, reverse=True)

        lines = ["# Job Comparison Report\n"]
        lines.append("| Rank | Company | Role | Score | Grade | Recommendation |")
        lines.append("|------|---------|------|-------|-------|----------------|")

        for i, r in enumerate(sorted_results, 1):
            lines.append(
                f"| {i} | {r.company} | {r.role} | {r.overall_score}/5.0 | "
                f"{r.grade.value} | {r.recommendation} |"
            )

        lines.append(f"\n**Best match:** {sorted_results[0].company} - {sorted_results[0].role}")
        return "\n".join(lines)

    async def _score_all_dimensions(
        self, cv_text: str, jd_text: str
    ) -> list[DimensionScore]:
        """Score all 10 dimensions using Groq with sequential rate-limited calls."""
        scores = []
        for dim in DIMENSIONS:
            try:
                raw = await self._groq.score_dimension(
                    dimension_name=dim["name"],
                    dimension_desc=dim["description"],
                    cv_excerpt=cv_text[:1500],
                    jd_excerpt=jd_text[:1500],
                )
                score_val = float(raw.get("score", 3.0))
                score_val = max(1.0, min(5.0, score_val))  # clamp
                scores.append(DimensionScore(
                    name=dim["name"],
                    score=score_val,
                    weight=dim["weight"],
                    reasoning=raw.get("reasoning", ""),
                    evidence=raw.get("evidence", []),
                ))
            except Exception as e:
                print(f"    [scoring] Dimension '{dim['name']}' failed: {e}")
                scores.append(DimensionScore(
                    name=dim["name"],
                    score=3.0,  # neutral default
                    weight=dim["weight"],
                    reasoning=f"Scoring failed: {e}",
                ))
        return scores

    async def _extract_job_info(self, jd_text: str) -> dict:
        """Extract company name and role from JD text using Groq."""
        try:
            return await self._groq.extract_json(
                f"Extract the company name and role title from this job description. "
                f"Return JSON: {{\"company\": \"str\", \"role\": \"str\"}}\n\n"
                f"{jd_text[:1000]}"
            )
        except Exception:
            return {}

    async def _fetch_jd(self, url: str) -> str:
        """Fetch job description text from a URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return ""
                    html = await resp.text()
                    # Strip HTML tags for a rough text extraction
                    text = re.sub(r"<[^>]+>", " ", html)
                    text = re.sub(r"\s+", " ", text).strip()
                    return text[:10000]  # limit to 10K chars
        except Exception as e:
            print(f"  [scoring] Fetch error: {e}")
            return ""

    def _get_recommendation(self, score: float, grade: Grade) -> str:
        """Generate recommendation text based on score."""
        if score >= 4.5:
            return "Strong match - apply immediately"
        elif score >= 4.0:
            return "Good match - worth applying"
        elif score >= 3.5:
            return "Decent - apply only with specific reason"
        elif score >= 3.0:
            return "Marginal - recommend against applying"
        elif score >= 2.5:
            return "Poor fit - do not apply"
        else:
            return "No match - skip"

    def _save_report(
        self,
        result: ScoringResult,
        match_analysis: dict,
        gap_data: dict,
    ) -> str:
        """Save evaluation report as markdown."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Determine next report number
        existing = list(REPORTS_DIR.glob("*.md"))
        nums = []
        for f in existing:
            match = re.match(r"(\d+)", f.stem)
            if match:
                nums.append(int(match.group(1)))
        next_num = max(nums, default=0) + 1

        # Build filename
        slug = re.sub(r"[^a-z0-9]+", "-", result.company.lower()).strip("-")
        filename = f"{next_num:03d}-{slug}-{result.evaluated_at}.md"
        filepath = REPORTS_DIR / filename

        # Generate report content
        content = generate_report(result, match_analysis, gap_data)
        filepath.write_text(content, encoding="utf-8")

        return str(filepath)
