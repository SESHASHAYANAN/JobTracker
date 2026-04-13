"""PDF generator — HTML → PDF conversion using WeasyPrint.

Pure Python — no Playwright or Node.js dependency.
Design spec adapted from career-ops pdf.md.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Optional

from agents.models import TailoredSection
from agents.cv_tailor.ats_optimizer import ATSOptimizer


class PDFGenerator:
    """Generate ATS-optimized PDF CVs from HTML templates.

    Design (from career-ops pdf.md):
    - Fonts: Space Grotesk (headings) + DM Sans (body) → fallback to system fonts
    - Header: name 24px bold + gradient line + contact row
    - Section headers: 13px uppercase, letter-spacing 0.05em
    - Body: 11px, line-height 1.5
    - Margins: 0.6in
    - Single-column layout (ATS-compliant)
    """

    def __init__(self):
        self._ats = ATSOptimizer()

    def render_template(
        self,
        sections: list[TailoredSection],
        competencies: list[str],
        profile: dict,
    ) -> str:
        """Render tailored CV sections into a complete HTML document."""
        company = profile.get("company", "")
        role = profile.get("role", "")

        # Build section HTML
        sections_html = []

        for section in sections:
            content = self._ats.normalize_unicode(section.tailored)
            paragraphs = self._text_to_html(content)
            sections_html.append(
                f'<div class="section">\n'
                f'  <h2 class="section-header">{html.escape(section.name)}</h2>\n'
                f'  <div class="section-content">{paragraphs}</div>\n'
                f'</div>'
            )

        # Competencies grid
        comp_tags = ""
        if competencies:
            tags = "".join(
                f'<span class="competency-tag">{html.escape(c)}</span>'
                for c in competencies
            )
            comp_tags = (
                f'<div class="section">\n'
                f'  <h2 class="section-header">Core Competencies</h2>\n'
                f'  <div class="competency-grid">{tags}</div>\n'
                f'</div>'
            )

        return self._get_template().replace(
            "{{SECTIONS}}", comp_tags + "\n".join(sections_html)
        ).replace(
            "{{COMPANY}}", html.escape(company)
        ).replace(
            "{{ROLE}}", html.escape(role)
        )

    def generate(self, html_content: str, output_path: Path, paper_format: str = "a4") -> Path:
        """Convert HTML to PDF using WeasyPrint.

        Falls back to saving HTML only if WeasyPrint is not available.
        """
        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(str(output_path))
            return output_path
        except ImportError:
            print("  [pdf] WeasyPrint not installed — saving HTML only")
            print("  [pdf] Install with: pip install weasyprint")
            html_path = output_path.with_suffix(".html")
            html_path.write_text(html_content, encoding="utf-8")
            return html_path
        except Exception as e:
            print(f"  [pdf] PDF generation error: {e}")
            html_path = output_path.with_suffix(".html")
            html_path.write_text(html_content, encoding="utf-8")
            return html_path

    def _text_to_html(self, text: str) -> str:
        """Convert plain text / markdown-ish text to HTML paragraphs."""
        lines = text.strip().split("\n")
        html_parts = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- ") or stripped.startswith("• "):
                bullet_text = html.escape(stripped[2:])
                html_parts.append(f'<li>{bullet_text}</li>')
            elif stripped.startswith("**") and stripped.endswith("**"):
                html_parts.append(f'<p class="role-title">{html.escape(stripped.strip("*"))}</p>')
            else:
                html_parts.append(f'<p>{html.escape(stripped)}</p>')

        # Wrap consecutive list items in <ul>
        result = []
        in_list = False
        for part in html_parts:
            if part.startswith("<li>"):
                if not in_list:
                    result.append("<ul>")
                    in_list = True
                result.append(part)
            else:
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append(part)
        if in_list:
            result.append("</ul>")

        return "\n    ".join(result)

    def _get_template(self) -> str:
        """Return the full HTML template with CSS styling."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CV — {{COMPANY}} — {{ROLE}}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:wght@400;500&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  @page {
    size: A4;
    margin: 0.6in;
  }

  body {
    font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
    font-size: 11px;
    line-height: 1.5;
    color: #1a1a2e;
    background: #ffffff;
  }

  .header {
    margin-bottom: 16px;
  }

  .header h1 {
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 4px;
  }

  .gradient-line {
    height: 2px;
    background: linear-gradient(to right, hsl(187, 74%, 32%), hsl(270, 70%, 45%));
    margin-bottom: 8px;
    border-radius: 1px;
  }

  .contact-row {
    font-size: 10px;
    color: #555;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .section {
    margin-bottom: 14px;
    page-break-inside: avoid;
  }

  .section-header {
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: hsl(187, 74%, 32%);
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 3px;
    margin-bottom: 8px;
  }

  .section-content p {
    margin-bottom: 4px;
  }

  .section-content ul {
    padding-left: 18px;
    margin-bottom: 6px;
  }

  .section-content li {
    margin-bottom: 2px;
  }

  .role-title {
    font-weight: 600;
    color: hsl(270, 70%, 45%);
    margin-top: 8px;
    margin-bottom: 2px;
  }

  .competency-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }

  .competency-tag {
    background: #f0f7ff;
    border: 1px solid #d0e4ff;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    color: #2563eb;
    font-weight: 500;
  }
</style>
</head>
<body>
  <div class="header">
    <h1>Candidate CV</h1>
    <div class="gradient-line"></div>
    <div class="contact-row">
      <span>Tailored for: {{COMPANY}} — {{ROLE}}</span>
    </div>
  </div>

  {{SECTIONS}}
</body>
</html>'''
