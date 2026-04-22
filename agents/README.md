# Career Intelligence Agent Suite

AI-powered job search automation using **Groq** (fast inference) + **Gemini** (long-context analysis).

Re-implements [career-ops](https://github.com/santifer/career-ops) pipeline as isolated Python agents — zero Claude dependency.

## Quick Start

```bash
# Install dependencies
pip install -r agents/requirements.txt

# Verify setup
python -m agents.cli --help

# Scan 45+ career portals (zero LLM tokens)
python -m agents.cli scan --dry-run

# Evaluate a job (requires cv.md)
python -m agents.cli score https://example.com/job

# Generate tailored CV
python -m agents.cli tailor https://example.com/job --cv cv.md

# Batch process URLs
python -m agents.cli batch urls.txt --cv cv.md --parallel 5

# View pipeline status
python -m agents.cli tracker --analytics
```

## Agents

| Agent | Purpose | LLM |
|-------|---------|-----|
| **JobScanAgent** | Scan 45+ portals (Greenhouse/Ashby/Lever APIs) | None (pure HTTP) |
| **ScoringAgent** | A-F scoring across 10 dimensions | Groq + Gemini |
| **CVTailorAgent** | ATS-optimized resume per JD | Groq + Gemini |
| **BatchAgent** | Parallel processing of 100+ URLs | Delegates to above |
| **TrackerAgent** | Pipeline status tracking + analytics | Groq (analytics only) |

## Configuration

Uses the same `.env` file as the existing backend:
- `GEMINI_API_KEY` — Google Gemini API key
- `GROQ_API_KEY` — Groq API key

## Architecture

```
agents/
├── __init__.py          # Package init
├── config.py            # Shared config (reads .env)
├── models.py            # Pydantic data models
├── cli.py               # Typer CLI entry point
├── llm/                 # LLM provider abstraction
│   ├── groq_client.py   # Groq with rate limiting
│   └── gemini_client.py # Gemini with retry
├── job_scan/            # (1) Portal Scanner
├── scoring/             # (2) 10-Dimension Scoring
├── cv_tailor/           # (3) ATS CV Generator
├── batch/               # (4) Parallel Processor
├── tracker/             # (5) Pipeline Tracker
├── data/                # Runtime data (gitignored)
│   ├── applications.md  # Application tracker
│   ├── pipeline.md      # URL inbox
│   ├── scan_history.tsv # Scan dedup
│   └── reports/         # Evaluation reports
└── templates/           # CV + report templates
```

## Zero Modifications Guarantee

This module is fully isolated — it does NOT import from or modify any files in `backend/`.
