"""Pipeline analytics — conversion rates, score distributions, and AI insights."""
from __future__ import annotations

from collections import Counter
from typing import Optional

from agents.models import PipelineEntry, TrackerSummary, PipelineAnalytics


def compute_analytics(
    entries: list[PipelineEntry],
    summary: TrackerSummary,
) -> PipelineAnalytics:
    """Compute detailed pipeline analytics from tracker entries.

    Generates:
    - Conversion rates between pipeline stages
    - Score distribution histogram
    - Activity by week
    - Actionable insights
    """
    if not entries:
        return PipelineAnalytics(summary=summary)

    # Conversion rates
    status_counts = summary.by_status
    total = summary.total_entries

    conversion_rates = {}
    stages = ["Evaluated", "Applied", "Interview", "Offer"]
    for i in range(len(stages) - 1):
        current = status_counts.get(stages[i], 0)
        next_stage = status_counts.get(stages[i + 1], 0)
        # Also count entries in later stages
        later_count = sum(
            status_counts.get(s, 0) for s in stages[i + 1:]
        )
        if current + later_count > 0:
            rate = later_count / (current + later_count) * 100
            conversion_rates[f"{stages[i]} -> {stages[i + 1]}"] = round(rate, 1)

    # Score distribution
    score_dist: dict[str, int] = {
        "4.5-5.0 (A)": 0,
        "4.0-4.4 (B)": 0,
        "3.5-3.9 (C)": 0,
        "3.0-3.4 (D)": 0,
        "2.5-2.9 (E)": 0,
        "Below 2.5 (F)": 0,
    }
    for e in entries:
        if e.score is None:
            continue
        if e.score >= 4.5:
            score_dist["4.5-5.0 (A)"] += 1
        elif e.score >= 4.0:
            score_dist["4.0-4.4 (B)"] += 1
        elif e.score >= 3.5:
            score_dist["3.5-3.9 (C)"] += 1
        elif e.score >= 3.0:
            score_dist["3.0-3.4 (D)"] += 1
        elif e.score >= 2.5:
            score_dist["2.5-2.9 (E)"] += 1
        else:
            score_dist["Below 2.5 (F)"] += 1

    # Weekly activity
    weekly_activity = []
    dates = [e.date for e in entries if e.date]
    if dates:
        date_counts = Counter(dates)
        for date, count in sorted(date_counts.items()):
            weekly_activity.append({"date": date, "count": count})

    # Generate insights
    insights = _generate_insights(entries, summary, conversion_rates, score_dist)

    return PipelineAnalytics(
        summary=summary,
        conversion_rates=conversion_rates,
        score_distribution=score_dist,
        weekly_activity=weekly_activity,
        insights=insights,
    )


def _generate_insights(
    entries: list[PipelineEntry],
    summary: TrackerSummary,
    conversion_rates: dict,
    score_dist: dict,
) -> list[str]:
    """Generate actionable insights from pipeline data."""
    insights = []

    # Scoring insights
    if summary.avg_score > 0:
        if summary.avg_score >= 4.0:
            insights.append(
                f"Strong targeting - avg score {summary.avg_score:.1f}/5.0 suggests good job-candidate alignment."
            )
        elif summary.avg_score < 3.5:
            insights.append(
                f"Low avg score ({summary.avg_score:.1f}/5.0) - consider refining search criteria "
                "to target better-matched roles."
            )

    # Conversion insights
    applied_count = summary.by_status.get("Applied", 0)
    evaluated_count = summary.by_status.get("Evaluated", 0)
    if evaluated_count > 5 and applied_count == 0:
        insights.append(
            f"You've evaluated {evaluated_count} roles but haven't applied to any yet. "
            "Consider applying to your top-scored opportunities."
        )

    # High-score unapplied
    high_score_unapplied = [
        e for e in entries
        if e.score and e.score >= 4.0 and e.status.value == "Evaluated"
    ]
    if high_score_unapplied:
        names = [f"{e.company} ({e.score:.1f})" for e in high_score_unapplied[:3]]
        insights.append(
            f"High-scoring unapplied: {', '.join(names)}. "
            "These are strong matches worth pursuing."
        )

    # PDF generation
    pdf_count = sum(1 for e in entries if e.pdf_generated)
    if pdf_count == 0 and summary.total_entries > 0:
        insights.append(
            "No tailored CVs generated yet. Run cv_tailor for your top matches."
        )

    # Volume insight
    if summary.total_entries >= 50:
        insights.append(
            f"You've evaluated {summary.total_entries} roles - focus on quality over quantity. "
            "Career-ops recommends applying only to scores >= 4.0."
        )

    return insights
