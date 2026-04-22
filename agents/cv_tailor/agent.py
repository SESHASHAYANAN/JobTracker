"""CVTailorAgent — generate ATS-optimized, JD-tailored CVs.

Split LLM strategy:
  - Groq: keyword extraction, competency grid (fast, ~0.3s each)
  - Gemini: section rewriting, bullet reordering (long-context, ~2s each)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import aiohttp

from agents.config import OUTPUT_DIR, TEMPLATES_DIR
from agents.models import TailoredCV, TailoredSection
from agents.llm.groq_client import GroqClient
from agents.llm.gemini_client import GeminiClient
from agents.scoring.archetype import detect_archetype
from agents.cv_tailor.keyword_extractor import extract_keywords, build_competency_grid
from agents.cv_tailor.section_rewriter import (
    rewrite_summary, reorder_experience, select_projects, inject_keywords,
)
from agents.cv_tailor.ats_optimizer import ATSOptimizer
from agents.cv_tailor.pdf_generator import PDFGenerator


class CVTailorAgent:
    """Generates ATS-optimized, JD-tailored CVs.

    Pipeline (from career-ops pdf.md):
    1. Read CV source (markdown or text)
    2. Extract 15-20 keywords from JD (Groq, ~0.3s)
    3. Detect archetype → adapt framing (Groq, ~0.3s)
    4. Rewrite Professional Summary with JD keywords (Gemini, ~2s)
    5. Reorder experience bullets by JD relevance (Gemini, ~2s)
    6. Build competency grid from JD requirements (Groq, ~0.3s)
    7. Inject keywords naturally into achievements (Gemini, ~2s)
    8. Check ATS compliance
    9. Generate HTML from template + tailored content
    10. Convert HTML → PDF
    """

    def __init__(self):
        self._groq = GroqClient()
        self._gemini = GeminiClient()
        self._ats = ATSOptimizer()
        self._pdf = PDFGenerator()

    async def tailor(
        self,
        cv_text: str,
        jd_text: str,
        output_dir: Optional[Path] = None,
        company: str = "",
        role: str = "",
    ) -> TailoredCV:
        """Generate a tailored CV for a specific JD.

        Args:
            cv_text: Full CV/resume text.
            jd_text: Full job description text.
            output_dir: Directory for output files.
            company: Company name (for filename).
            role: Role title (for filename).

        Returns:
            TailoredCV with paths to generated files.
        """
        out_dir = output_dir or OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"  [cv-tailor] Tailoring CV for {company or 'target'} — {role or 'role'}")

        # 1. Parse CV into sections
        sections = self._parse_cv_sections(cv_text)
        print(f"  [cv-tailor] Parsed {len(sections)} CV sections")

        # 2. Extract keywords from JD (Groq — fast)
        print("  [cv-tailor] Step 1/6: Extracting JD keywords...")
        keywords = await extract_keywords(jd_text, self._groq, count=20)
        print(f"  [cv-tailor] Found {len(keywords)} keywords: {', '.join(keywords[:8])}...")

        # 3. Detect archetype (Groq — fast)
        print("  [cv-tailor] Step 2/6: Detecting archetype...")
        archetype, _ = await detect_archetype(jd_text, self._groq)
        print(f"  [cv-tailor] Archetype: {archetype.value}")

        # 4. Build competency grid (Groq — fast)
        print("  [cv-tailor] Step 3/6: Building competency grid...")
        competencies = await build_competency_grid(keywords, jd_text, self._groq)

        # 5. Rewrite sections (Gemini — long-context)
        tailored_sections: list[TailoredSection] = []

        # Professional Summary
        if "summary" in sections:
            print("  [cv-tailor] Step 4/6: Rewriting summary...")
            new_summary = await rewrite_summary(
                sections["summary"], keywords, archetype.value, jd_text, self._gemini
            )
            tailored_sections.append(TailoredSection(
                name="Professional Summary",
                original=sections["summary"],
                tailored=new_summary,
                keywords_used=keywords[:5],
            ))

        # Experience
        if "experience" in sections:
            print("  [cv-tailor] Step 5/6: Reordering experience...")
            new_experience = await reorder_experience(
                sections["experience"], jd_text, keywords, self._gemini
            )
            tailored_sections.append(TailoredSection(
                name="Work Experience",
                original=sections["experience"],
                tailored=new_experience,
                keywords_used=[k for k in keywords if k.lower() in new_experience.lower()],
            ))

        # Projects
        if "projects" in sections:
            print("  [cv-tailor] Selecting top projects...")
            new_projects = await select_projects(
                sections["projects"], jd_text, keywords, self._gemini
            )
            tailored_sections.append(TailoredSection(
                name="Projects",
                original=sections["projects"],
                tailored=new_projects,
                keywords_used=[k for k in keywords if k.lower() in new_projects.lower()],
            ))

        # Skills — inject remaining keywords
        if "skills" in sections:
            print("  [cv-tailor] Step 6/6: Injecting keywords into skills...")
            new_skills = await inject_keywords(
                sections["skills"], keywords, jd_text, self._gemini
            )
            tailored_sections.append(TailoredSection(
                name="Skills",
                original=sections["skills"],
                tailored=new_skills,
                keywords_used=[k for k in keywords if k.lower() in new_skills.lower()],
            ))

        # Pass through unchanged sections
        for section_name in ["education", "certifications"]:
            if section_name in sections:
                tailored_sections.append(TailoredSection(
                    name=section_name.title(),
                    original=sections[section_name],
                    tailored=sections[section_name],
                ))

        # 6. Compute keyword coverage
        all_tailored = " ".join(s.tailored for s in tailored_sections).lower()
        found = [k for k in keywords if k.lower() in all_tailored]
        coverage = len(found) / len(keywords) * 100 if keywords else 0

        # 7. ATS compliance check
        ats_score = self._ats.compute_ats_score(
            tailored_sections, keywords, found
        )

        # 8. Generate HTML
        slug = re.sub(r"[^a-z0-9]+", "-", (company or "company").lower()).strip("-")
        from datetime import datetime
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        base_name = f"cv-{slug}-{date_str}"

        html_content = self._pdf.render_template(
            sections=tailored_sections,
            competencies=competencies,
            profile={"company": company, "role": role},
        )
        html_path = out_dir / f"{base_name}.html"
        html_path.write_text(html_content, encoding="utf-8")

        # 9. Generate PDF
        pdf_path = out_dir / f"{base_name}.pdf"
        try:
            self._pdf.generate(html_content, pdf_path)
            print(f"  [cv-tailor] [OK] PDF generated: {pdf_path}")
        except Exception as e:
            print(f"  [cv-tailor] [WARN] PDF generation failed: {e}")
            print(f"  [cv-tailor]   HTML saved at: {html_path}")
            pdf_path = None

        result = TailoredCV(
            sections=tailored_sections,
            keywords_injected=found,
            keyword_coverage=round(coverage, 1),
            ats_score=round(ats_score, 1),
            html_path=str(html_path),
            pdf_path=str(pdf_path) if pdf_path else None,
        )

        print(f"  [cv-tailor] [OK] Keyword coverage: {result.keyword_coverage}%, ATS score: {result.ats_score}%")
        return result

    async def tailor_from_url(
        self,
        cv_text: str,
        jd_url: str,
        output_dir: Optional[Path] = None,
    ) -> TailoredCV:
        """Tailor CV from a JD URL by fetching it first."""
        print(f"  [cv-tailor] Fetching JD from: {jd_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(jd_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    html = await resp.text()
                    jd_text = re.sub(r"<[^>]+>", " ", html)
                    jd_text = re.sub(r"\s+", " ", jd_text).strip()[:10000]
        except Exception as e:
            print(f"  [cv-tailor] Failed to fetch JD: {e}")
            return TailoredCV()

        return await self.tailor(cv_text, jd_text, output_dir)

    def _parse_cv_sections(self, cv_text: str) -> dict[str, str]:
        """Parse a CV into named sections.

        Supports markdown headings (##) and common section titles.
        """
        sections: dict[str, str] = {}
        current_section = "summary"
        current_lines: list[str] = []

        section_map = {
            "summary": ["summary", "professional summary", "profile", "about", "objective"],
            "experience": ["experience", "work experience", "employment", "work history"],
            "projects": ["projects", "portfolio", "personal projects", "side projects"],
            "education": ["education", "academic", "qualifications", "degrees"],
            "skills": ["skills", "technical skills", "core competencies", "technologies"],
            "certifications": ["certifications", "certificates", "licenses", "credentials"],
        }

        for line in cv_text.split("\n"):
            stripped = line.strip().lower()
            # Check if this is a section header
            header_text = stripped.lstrip("#").strip()

            matched_section = None
            for section_key, aliases in section_map.items():
                if any(alias in header_text for alias in aliases):
                    matched_section = section_key
                    break

            if matched_section and matched_section != current_section:
                # Save current section
                if current_lines:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = matched_section
                current_lines = []
            else:
                current_lines.append(line)

        # Save last section
        if current_lines:
            sections[current_section] = "\n".join(current_lines).strip()

        return sections
