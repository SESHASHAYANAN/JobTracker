"""Role archetype detection — classify JDs into 6 career-ops archetypes.

Uses Groq for fast classification (~0.3s per JD).
Adapted from career-ops modes/_shared.md archetype table.
"""
from __future__ import annotations

from agents.models import Archetype
from agents.llm.groq_client import GroqClient


# Archetype definitions with signal keywords
ARCHETYPE_SIGNALS: dict[str, list[str]] = {
    "llmops": [
        "observability", "evals", "evaluation", "pipelines", "monitoring",
        "reliability", "mlops", "model serving", "inference", "deployment",
        "cost optimization", "latency", "throughput", "production ml",
    ],
    "agentic": [
        "agent", "agents", "agentic", "hitl", "human-in-the-loop",
        "orchestration", "workflow", "multi-agent", "tool use", "tool calling",
        "function calling", "autonomous", "chain-of-thought",
    ],
    "technical_pm": [
        "prd", "roadmap", "discovery", "stakeholder", "product manager",
        "product management", "user research", "requirements", "prioritization",
        "kpi", "okr", "go-to-market", "product strategy",
    ],
    "solutions_arch": [
        "architecture", "enterprise", "integration", "systems design",
        "solution", "technical pre-sales", "rfc", "design doc",
        "distributed systems", "microservices", "api design",
    ],
    "forward_deployed": [
        "client-facing", "deploy", "prototype", "fast delivery", "field",
        "customer success", "implementation", "onboarding", "poc",
        "proof of concept", "demo", "technical account",
    ],
    "transformation": [
        "change management", "adoption", "enablement", "transformation",
        "digital transformation", "organizational change", "training",
        "process improvement", "center of excellence",
    ],
}


async def detect_archetype(
    jd_text: str, groq: GroqClient
) -> tuple[Archetype, float]:
    """Detect the role archetype from a job description.

    Uses a two-pass approach:
    1. Quick keyword scan for signal detection
    2. LLM classification for ambiguous cases

    Returns:
        Tuple of (Archetype enum, confidence float 0-1)
    """
    # Pass 1: Keyword-based scoring
    scores: dict[str, int] = {}
    jd_lower = jd_text.lower()

    for archetype, signals in ARCHETYPE_SIGNALS.items():
        count = sum(1 for s in signals if s in jd_lower)
        scores[archetype] = count

    # Find top two candidates
    sorted_archetypes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_name, top_score = sorted_archetypes[0]
    second_name, second_score = sorted_archetypes[1] if len(sorted_archetypes) > 1 else ("", 0)

    # If strong keyword signal, use it directly
    if top_score >= 4 and top_score > second_score * 2:
        try:
            return Archetype(top_name), min(0.9, top_score / 10.0)
        except ValueError:
            pass

    # Pass 2: LLM classification for ambiguous cases
    try:
        categories = [a.value for a in Archetype if a != Archetype.GENERAL]
        result = await groq.classify(
            text=jd_text[:2000],
            categories=categories,
            context=(
                "Classify this job description into one of these role archetypes:\n"
                "- llmops: ML/AI infrastructure, model serving, observability, evals\n"
                "- agentic: AI agents, orchestration, tool use, multi-agent systems\n"
                "- technical_pm: Product management with technical focus\n"
                "- solutions_arch: Enterprise architecture, systems design, integrations\n"
                "- forward_deployed: Client-facing, rapid prototyping, field deployments\n"
                "- transformation: Organizational change, AI adoption, enablement\n"
                "- general: Does not clearly fit any specific archetype\n"
            ),
        )
        try:
            archetype = Archetype(result.lower().strip())
            # Combine keyword and LLM confidence
            keyword_conf = min(scores.get(archetype.value, 0) / 8.0, 0.5)
            return archetype, min(0.95, 0.5 + keyword_conf)
        except ValueError:
            pass
    except Exception as e:
        print(f"    [archetype] LLM classification failed: {e}")

    # Fallback: use keyword winner or general
    try:
        return Archetype(top_name), min(0.5, top_score / 8.0)
    except ValueError:
        return Archetype.GENERAL, 0.3
