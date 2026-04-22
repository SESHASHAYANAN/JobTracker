"""Batch worker — processes a single URL through the scoring + CV pipeline.

Equivalent to career-ops `claude -p` sub-process worker.
"""
from __future__ import annotations

from agents.config import AUTO_PDF_SCORE
from agents.scoring.agent import ScoringAgent
from agents.cv_tailor.agent import CVTailorAgent
from agents.tracker.agent import TrackerAgent
from agents.models import JobStatus


class BatchWorker:
    """Individual URL processing worker.

    For each URL:
    1. Fetch JD from URL
    2. Score with ScoringAgent
    3. Generate tailored CV (if score >= threshold)
    4. Register in tracker
    """

    def __init__(self):
        self._scorer = ScoringAgent()
        self._tailor = CVTailorAgent()
        self._tracker = TrackerAgent()

    async def process(
        self,
        url: str,
        cv_text: str,
        report_num: int,
        generate_pdf: bool = True,
    ) -> dict:
        """Process a single URL through the full pipeline.

        Returns dict with: score, report_num, report_path, pdf_path.
        """
        # 1. Score the job
        result = await self._scorer.evaluate_url(url, cv_text)

        # 2. Generate PDF if score is high enough
        pdf_generated = False
        pdf_path = None
        if generate_pdf and result.overall_score >= AUTO_PDF_SCORE:
            try:
                # Re-fetch JD for tailoring
                import aiohttp, re
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        html = await resp.text()
                        jd_text = re.sub(r"<[^>]+>", " ", html)
                        jd_text = re.sub(r"\s+", " ", jd_text).strip()[:10000]

                tailored = await self._tailor.tailor(
                    cv_text=cv_text,
                    jd_text=jd_text,
                    company=result.company,
                    role=result.role,
                )
                pdf_generated = tailored.pdf_path is not None
                pdf_path = tailored.pdf_path
            except Exception as e:
                print(f"    [worker] PDF generation failed: {e}")

        # 3. Register in tracker
        from agents.models import PipelineEntry
        entry = PipelineEntry(
            number=report_num,
            date=result.evaluated_at,
            company=result.company,
            role=result.role,
            score=result.overall_score,
            status=JobStatus.EVALUATED,
            pdf_generated=pdf_generated,
            report_link=result.report_path,
            notes=f"{result.grade.value} — {result.recommendation}",
        )
        await self._tracker.add_entry(entry)

        return {
            "score": result.overall_score,
            "report_num": report_num,
            "report_path": result.report_path,
            "pdf_path": pdf_path,
            "grade": result.grade.value,
        }
