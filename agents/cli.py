"""Career Intelligence CLI — Typer-based command-line interface.

Usage:
    python -m agents.cli scan                    # Scan 45+ portals
    python -m agents.cli scan --company Anthropic # Scan single company
    python -m agents.cli scan --dry-run           # Preview without saving

    python -m agents.cli score <JD_URL>          # Evaluate a single job
    python -m agents.cli score --jd-file job.md  # Evaluate from file

    python -m agents.cli tailor <JD_URL>         # Generate tailored CV
    python -m agents.cli tailor --cv cv.md --jd job.md

    python -m agents.cli batch urls.txt          # Process 100+ URLs
    python -m agents.cli batch --retry-failed    # Retry failed items
    python -m agents.cli batch --status          # Show batch progress

    python -m agents.cli tracker                 # Show pipeline status
    python -m agents.cli tracker --analytics     # Show conversion analytics
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents.config import validate_config

app = typer.Typer(
    name="career-agents",
    help="Career Intelligence Agent Suite -- Groq + Gemini powered job search automation.",
    no_args_is_help=True,
)
console = Console(highlight=False)


def _run_async(coro):
    """Run an async coroutine."""
    return asyncio.run(coro)


# ── Scan Command ─────────────────────────────────────────────────────

@app.command()
def scan(
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Scan a specific company"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without saving"),
    config: Optional[Path] = typer.Option(None, "--config", help="Custom portals config YAML"),
):
    """Scan 45+ career portals for new job listings (zero LLM tokens)."""
    console.print(Panel("[bold cyan]JobScanAgent[/] -- Portal Scanner", border_style="cyan"))

    from agents.job_scan.agent import JobScanAgent
    agent = JobScanAgent(config_path=config)
    result = _run_async(agent.scan_all(dry_run=dry_run, company_filter=company))

    if result.new_offers:
        console.print(f"\n[green][OK] Found {len(result.new_offers)} new offers[/]")
    else:
        console.print("\n[yellow]No new offers found.[/]")


# ── Score Command ────────────────────────────────────────────────────

@app.command()
def score(
    url: Optional[str] = typer.Argument(None, help="Job posting URL to evaluate"),
    jd_file: Optional[Path] = typer.Option(None, "--jd-file", "-j", help="JD text file"),
    cv_file: Optional[Path] = typer.Option(None, "--cv", help="CV/resume file (text or markdown)"),
    company: Optional[str] = typer.Option(None, "--company", help="Company name"),
    role: Optional[str] = typer.Option(None, "--role", help="Role title"),
):
    """Evaluate a job description using A-F scoring across 10 dimensions."""
    warnings = validate_config()
    for w in warnings:
        console.print(f"[yellow][WARN] {w}[/]")

    console.print(Panel("[bold green]ScoringAgent[/] -- Job Evaluator", border_style="green"))

    # Load CV
    cv_text = _load_cv(cv_file)
    if not cv_text:
        console.print("[red]Error: No CV provided. Use --cv or create agents/data/cv.md[/]")
        raise typer.Exit(1)

    # Load JD
    from agents.scoring.agent import ScoringAgent
    agent = ScoringAgent()

    if url:
        result = _run_async(agent.evaluate_url(url, cv_text))
    elif jd_file and jd_file.exists():
        jd_text = jd_file.read_text(encoding="utf-8")
        result = _run_async(agent.evaluate(jd_text, cv_text, company=company or "", role=role or ""))
    else:
        console.print("[red]Error: Provide a URL or --jd-file[/]")
        raise typer.Exit(1)

    # Display results
    _display_score_result(result)


# ── Tailor Command ───────────────────────────────────────────────────

@app.command()
def tailor(
    url: Optional[str] = typer.Argument(None, help="Job posting URL"),
    jd_file: Optional[Path] = typer.Option(None, "--jd-file", "-j", help="JD text file"),
    cv_file: Optional[Path] = typer.Option(None, "--cv", help="CV/resume file"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    company: Optional[str] = typer.Option(None, "--company", help="Company name"),
    role: Optional[str] = typer.Option(None, "--role", help="Role title"),
):
    """Generate an ATS-optimized, JD-tailored CV."""
    console.print(Panel("[bold magenta]CVTailorAgent[/] -- Resume Optimizer", border_style="magenta"))

    cv_text = _load_cv(cv_file)
    if not cv_text:
        console.print("[red]Error: No CV provided. Use --cv or create agents/data/cv.md[/]")
        raise typer.Exit(1)

    from agents.cv_tailor.agent import CVTailorAgent
    agent = CVTailorAgent()

    if url:
        result = _run_async(agent.tailor_from_url(cv_text, url, output_dir))
    elif jd_file and jd_file.exists():
        jd_text = jd_file.read_text(encoding="utf-8")
        result = _run_async(agent.tailor(cv_text, jd_text, output_dir, company=company or "", role=role or ""))
    else:
        console.print("[red]Error: Provide a URL or --jd-file[/]")
        raise typer.Exit(1)

    if result.pdf_path:
        console.print(f"\n[green][OK] PDF generated: {result.pdf_path}[/]")
    if result.html_path:
        console.print(f"[green][OK] HTML generated: {result.html_path}[/]")
    console.print(f"[cyan]  Keyword coverage: {result.keyword_coverage}%[/]")
    console.print(f"[cyan]  ATS score: {result.ats_score}%[/]")


# ── Batch Command ────────────────────────────────────────────────────

@app.command()
def batch(
    input_file: Optional[Path] = typer.Argument(None, help="File with URLs (one per line)"),
    cv_file: Optional[Path] = typer.Option(None, "--cv", help="CV/resume file"),
    concurrency: int = typer.Option(5, "--parallel", "-p", help="Number of parallel workers"),
    retry_failed: bool = typer.Option(False, "--retry-failed", help="Retry previously failed jobs"),
    status: bool = typer.Option(False, "--status", help="Show batch processing status"),
    no_pdf: bool = typer.Option(False, "--no-pdf", help="Skip PDF generation"),
):
    """Process 100+ job URLs in parallel with scoring + CV tailoring."""
    console.print(Panel("[bold yellow]BatchAgent[/] -- Parallel Processor", border_style="yellow"))

    from agents.batch.agent import BatchAgent
    agent = BatchAgent(concurrency=concurrency)

    if status:
        batch_status = agent.get_status()
        _display_batch_status(batch_status)
        return

    cv_text = _load_cv(cv_file)
    if not cv_text:
        console.print("[red]Error: No CV provided. Use --cv or create agents/data/cv.md[/]")
        raise typer.Exit(1)

    if retry_failed:
        result = _run_async(agent.retry_failed(cv_text))
    elif input_file and input_file.exists():
        result = _run_async(agent.process_file(input_file, cv_text, concurrency))
    else:
        console.print("[red]Error: Provide an input file with URLs or --retry-failed[/]")
        raise typer.Exit(1)

    console.print(f"\n[green][OK] Completed: {result.completed}/{result.total}[/]")


# ── Tracker Command ──────────────────────────────────────────────────

@app.command()
def tracker(
    analytics: bool = typer.Option(False, "--analytics", "-a", help="Show pipeline analytics"),
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    update_company: Optional[str] = typer.Option(None, "--update", help="Update status for company"),
    new_status: Optional[str] = typer.Option(None, "--set-status", help="New status to set"),
    role_name: Optional[str] = typer.Option(None, "--role", help="Role name for update"),
):
    """View and manage the application pipeline tracker."""
    console.print(Panel("[bold blue]TrackerAgent[/] -- Pipeline Status", border_style="blue"))

    from agents.tracker.agent import TrackerAgent
    agent = TrackerAgent()

    if update_company and new_status:
        _run_async(agent.update_status(update_company, role_name or "", new_status))
        return

    if analytics:
        result = _run_async(agent.get_analytics())
        _display_analytics(result)
    else:
        _run_async(agent.print_status())


# ── Helpers ──────────────────────────────────────────────────────────

def _load_cv(cv_file: Optional[Path] = None) -> str:
    """Load CV text from file or default location."""
    if cv_file and cv_file.exists():
        return cv_file.read_text(encoding="utf-8")

    # Try default locations
    from agents.config import DATA_DIR, AGENTS_DIR
    for candidate in [
        DATA_DIR / "cv.md",
        AGENTS_DIR.parent / "cv.md",
        Path("cv.md"),
    ]:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    return ""


def _display_score_result(result):
    """Display scoring result with Rich formatting."""
    from agents.models import ScoringResult

    table = Table(title=f"Evaluation: {result.company} - {result.role}")
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", justify="center")
    table.add_column("Weight", justify="center")
    table.add_column("Reasoning", max_width=50)

    for dim in result.dimensions:
        bar = "█" * int(dim.score) + "░" * (5 - int(dim.score))
        table.add_row(
            dim.name,
            f"{bar} {dim.score:.1f}",
            f"{dim.weight:.0%}",
            dim.reasoning[:50] + "..." if len(dim.reasoning) > 50 else dim.reasoning,
        )

    console.print(table)
    console.print(f"\n[bold]Overall: {result.overall_score}/5.0 -- Grade {result.grade.value}[/]")
    console.print(f"[{'green' if result.overall_score >= 4.0 else 'yellow'}]{result.recommendation}[/]")
    if result.report_path:
        console.print(f"\nReport saved: {result.report_path}")


def _display_batch_status(status: dict):
    """Display batch processing status."""
    table = Table(title="Batch Processing Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total", str(status.get("total", 0)))
    table.add_row("Pending", str(status.get("pending", 0)))
    table.add_row("Processing", str(status.get("processing", 0)))
    table.add_row("Completed", f"[green]{status.get('completed', 0)}[/]")
    table.add_row("Failed", f"[red]{status.get('failed', 0)}[/]")
    table.add_row("Avg Score", f"{status.get('avg_score', 0):.1f}/5.0")

    console.print(table)


def _display_analytics(analytics):
    """Display pipeline analytics."""
    from agents.models import PipelineAnalytics

    # Summary
    s = analytics.summary
    console.print(f"\n[bold]Pipeline: {s.total_entries} entries, avg score {s.avg_score:.1f}/5.0[/]\n")

    # Score distribution
    if analytics.score_distribution:
        table = Table(title="Score Distribution")
        table.add_column("Range", style="cyan")
        table.add_column("Count", justify="right")
        for k, v in analytics.score_distribution.items():
            table.add_row(k, str(v))
        console.print(table)

    # Conversion rates
    if analytics.conversion_rates:
        console.print("\n[bold]Conversion Rates:[/]")
        for stage, rate in analytics.conversion_rates.items():
            console.print(f"  {stage}: {rate}%")

    # Insights
    if analytics.insights:
        console.print("\n[bold]Insights:[/]")
        for insight in analytics.insights:
            console.print(f"  * {insight}")


# ── Entry Point ──────────────────────────────────────────────────────

def main():
    app()


if __name__ == "__main__":
    main()
