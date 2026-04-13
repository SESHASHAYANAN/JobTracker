"""Career Intelligence Agent Suite — Groq + Gemini powered job search automation.

Re-implements career-ops (santifer/career-ops) pipeline as isolated Python agents:
  - JobScanAgent:  Scrape 45+ career portals (zero LLM tokens)
  - ScoringAgent:  A-F scoring across 10 dimensions
  - CVTailorAgent: ATS-optimized resume per JD
  - BatchAgent:    Parallel processing of 100+ URLs
  - TrackerAgent:  Pipeline status tracking

All code isolated in /agents — zero modifications to existing codebase.
"""

__version__ = "1.0.0"
__author__ = "JobTracker Intelligence Suite"
