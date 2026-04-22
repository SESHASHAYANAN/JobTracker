"""Markdown report generator for scoring evaluations.

Outputs structured evaluation reports matching career-ops format (blocks A-F).
"""
from __future__ import annotations

from agents.models import ScoringResult
from agents.scoring.dimensions import get_grade_label


def generate_report(
    result: ScoringResult,
    match_analysis: dict,
    gap_data: dict,
) -> str:
    """Generate a structured evaluation report in markdown.

    Report structure (inspired by career-ops oferta.md):
    A) Role Summary
    B) CV Match
    C) Dimension Scores
    D) Gap Analysis
    E) Keywords
    F) Recommendation
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Evaluation: {result.company} — {result.role}\n")
    lines.append(f"**Date:** {result.evaluated_at}")
    lines.append(f"**URL:** {result.url or 'N/A'}")
    lines.append(f"**Archetype:** {result.archetype.value} (confidence: {result.archetype_confidence:.0%})")
    lines.append(f"**Score:** {result.overall_score}/5.0")
    lines.append(f"**Grade:** {get_grade_label(result.overall_score)}")
    lines.append(f"**Recommendation:** {result.recommendation}")
    lines.append("")
    lines.append("---\n")

    # A) Role Summary
    lines.append("## A) Role Summary\n")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Company | {result.company} |")
    lines.append(f"| Role | {result.role} |")
    lines.append(f"| Archetype | {result.archetype.value} |")
    lines.append(f"| Overall Score | {result.overall_score}/5.0 ({result.grade.value}) |")
    lines.append("")

    # B) CV Match
    lines.append("## B) CV Match Analysis\n")
    match_summary = match_analysis.get("match_summary", "No analysis available.")
    lines.append(f"{match_summary}\n")

    matched_reqs = match_analysis.get("matched_requirements", [])
    if matched_reqs:
        lines.append("### Matched Requirements\n")
        lines.append("| Requirement | CV Evidence | Strength |")
        lines.append("|-------------|-------------|----------|")
        for req in matched_reqs[:15]:
            if isinstance(req, dict):
                lines.append(
                    f"| {req.get('requirement', '')} | "
                    f"{req.get('cv_evidence', '')} | "
                    f"{req.get('strength', '')}/5 |"
                )
        lines.append("")

    strengths = match_analysis.get("strengths", [])
    if strengths:
        lines.append("### Candidate Strengths\n")
        for s in strengths:
            lines.append(f"- {s}")
        lines.append("")

    # C) Dimension Scores
    lines.append("## C) Dimension Scores\n")
    lines.append("| Dimension | Score | Weight | Reasoning |")
    lines.append("|-----------|-------|--------|-----------|")
    for dim in result.dimensions:
        bar = "█" * int(dim.score) + "░" * (5 - int(dim.score))
        lines.append(
            f"| {dim.name} | {bar} {dim.score:.1f}/5.0 | "
            f"{dim.weight:.0%} | {dim.reasoning[:80]}{'...' if len(dim.reasoning) > 80 else ''} |"
        )
    lines.append("")
    lines.append(f"**Weighted Average: {result.overall_score}/5.0 → Grade {result.grade.value}**\n")

    # D) Gap Analysis
    lines.append("## D) Gap Analysis\n")
    gaps = gap_data.get("gaps", [])
    if gaps:
        lines.append("| Gap | Severity | Mitigation |")
        lines.append("|-----|----------|------------|")
        for gap in gaps:
            if isinstance(gap, dict):
                lines.append(
                    f"| {gap.get('gap', '')} | "
                    f"{gap.get('severity', 'unknown')} | "
                    f"{gap.get('mitigation', '')} |"
                )
        lines.append("")
    else:
        lines.append("No significant gaps identified.\n")

    # E) Keywords
    kw_found = match_analysis.get("keywords_found", [])
    kw_missing = match_analysis.get("keywords_missing", [])
    lines.append("## E) Keywords Extracted\n")
    if kw_found:
        lines.append(f"**Found in CV ({len(kw_found)}):** {', '.join(kw_found[:20])}\n")
    if kw_missing:
        lines.append(f"**Missing from CV ({len(kw_missing)}):** {', '.join(kw_missing[:20])}\n")

    # F) Recommendation
    lines.append("## F) Recommendation\n")
    lines.append(f"**{result.recommendation}**\n")
    if result.overall_score >= 4.0:
        lines.append(
            "This role is a good fit. Consider generating a tailored CV with:\n"
            f"```\npython -m agents.cli tailor --jd-url \"{result.url}\"\n```\n"
        )
    elif result.overall_score >= 3.5:
        lines.append(
            "This role has potential but may not be the strongest fit. "
            "Consider if you have specific reasons to apply beyond the score.\n"
        )
    else:
        lines.append(
            "This role is not recommended. Focus your energy on better-matched opportunities.\n"
        )

    return "\n".join(lines)
