"""JobScanAgent — scan 45+ career portals via Greenhouse/Ashby/Lever APIs.

Zero LLM tokens — pure HTTP + JSON parsing.
Ported from career-ops scan.mjs with identical dedup + filter logic.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp

from agents.config import (
    DATA_DIR, SCAN_CONCURRENCY, SCAN_FETCH_TIMEOUT, SCAN_USER_AGENT,
    PIPELINE_FILE, SCAN_HISTORY_FILE, APPLICATIONS_FILE,
)
from agents.models import ScannedJob, ScanResult, PortalConfig, TitleFilterConfig
from agents.job_scan.portals import load_portals_config, detect_api
from agents.job_scan.parsers import PARSERS
from agents.job_scan.filters import TitleFilter, Deduplicator


class JobScanAgent:
    """Scans career portals for new job listings.

    Architecture (mirrors career-ops scan.mjs):
    1. Load portal config from portals_config.yaml
    2. Detect API type per portal (Greenhouse/Ashby/Lever)
    3. Parallel HTTP fetch with concurrency limit
    4. Title filtering (positive + negative keywords)
    5. Dedup against scan_history.tsv + pipeline.md + applications.md
    6. Append new offers to pipeline.md + scan_history.tsv

    Zero LLM tokens — pure HTTP + JSON.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path
        self._portals: list[PortalConfig] = []
        self._title_filter: Optional[TitleFilter] = None
        self._deduplicator = Deduplicator(DATA_DIR)

    def _load_config(self):
        """Load portal and filter configuration."""
        config = load_portals_config(self._config_path)
        self._portals = config["portals"]
        self._title_filter = TitleFilter(
            positive=config["title_filter"].positive,
            negative=config["title_filter"].negative,
        )

    async def scan_all(
        self,
        dry_run: bool = False,
        company_filter: Optional[str] = None,
    ) -> ScanResult:
        """Scan all enabled portals and return results.

        Args:
            dry_run: If True, preview without writing files.
            company_filter: If set, only scan companies matching this name.

        Returns:
            ScanResult with all new offers found.
        """
        self._load_config()
        self._deduplicator.load()

        # Filter to enabled portals with detectable APIs
        targets = []
        skipped = 0
        for portal in self._portals:
            if not portal.enabled:
                continue
            if company_filter and company_filter.lower() not in portal.name.lower():
                continue
            api_info = detect_api(portal)
            if api_info:
                targets.append((portal, api_info))
            else:
                skipped += 1

        print(f"Scanning {len(targets)} companies via API ({skipped} skipped — no API detected)")
        if dry_run:
            print("(dry run — no files will be written)\n")

        # Parallel fetch with concurrency limit
        result = ScanResult(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            companies_scanned=len(targets),
        )

        semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=SCAN_FETCH_TIMEOUT),
            headers={"User-Agent": SCAN_USER_AGENT},
        ) as session:
            tasks = [
                self._scan_company(session, semaphore, portal, api_info, result)
                for portal, api_info in targets
            ]
            await asyncio.gather(*tasks)

        # Write results
        if not dry_run and result.new_offers:
            self._append_to_pipeline(result.new_offers)
            self._append_to_scan_history(result.new_offers, result.date)

        # Print summary
        self._print_summary(result, dry_run)
        return result

    async def scan_company(self, company_name: str) -> list[ScannedJob]:
        """Scan a single company by name."""
        result = await self.scan_all(dry_run=False, company_filter=company_name)
        return result.new_offers

    async def _scan_company(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        portal: PortalConfig,
        api_info: dict,
        result: ScanResult,
    ):
        """Fetch and process jobs from a single company."""
        async with semaphore:
            try:
                async with session.get(api_info["url"]) as resp:
                    if resp.status != 200:
                        result.errors.append({
                            "company": portal.name,
                            "error": f"HTTP {resp.status}",
                        })
                        return

                    json_data = await resp.json()
                    parser = PARSERS.get(api_info["type"])
                    if not parser:
                        return

                    jobs = parser(json_data, portal.name)
                    result.total_found += len(jobs)

                    for job in jobs:
                        # Title filter
                        if self._title_filter and not self._title_filter.matches(job.title):
                            result.filtered_by_title += 1
                            continue

                        # Dedup check
                        if self._deduplicator.is_seen(job.url, job.company, job.title):
                            result.duplicates += 1
                            continue

                        # Mark as seen (intra-scan dedup)
                        self._deduplicator.mark_seen(job.url, job.company, job.title)
                        job.source = f"{api_info['type']}-api"
                        result.new_offers.append(job)

            except asyncio.TimeoutError:
                result.errors.append({"company": portal.name, "error": "Timeout"})
            except Exception as e:
                result.errors.append({"company": portal.name, "error": str(e)})

    def _append_to_pipeline(self, offers: list[ScannedJob]):
        """Append new offers to pipeline.md."""
        PIPELINE_FILE.parent.mkdir(parents=True, exist_ok=True)

        if not PIPELINE_FILE.exists():
            PIPELINE_FILE.write_text(
                "# Job Pipeline\n\n## Pending\n\n## Processed\n",
                encoding="utf-8",
            )

        text = PIPELINE_FILE.read_text(encoding="utf-8")
        new_lines = "\n".join(
            f"- [ ] {o.url} | {o.company} | {o.title}" for o in offers
        )

        # Find "## Pending" section
        marker = "## Pending"
        idx = text.find(marker)
        if idx == -1:
            # Add section
            text += f"\n{marker}\n\n{new_lines}\n"
        else:
            # Insert after marker
            after = idx + len(marker)
            next_section = text.find("\n## ", after)
            insert_at = next_section if next_section != -1 else len(text)
            text = text[:insert_at] + "\n" + new_lines + "\n" + text[insert_at:]

        PIPELINE_FILE.write_text(text, encoding="utf-8")

    def _append_to_scan_history(self, offers: list[ScannedJob], date: str):
        """Append new offers to scan_history.tsv."""
        SCAN_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        if not SCAN_HISTORY_FILE.exists():
            SCAN_HISTORY_FILE.write_text(
                "url\tfirst_seen\tportal\ttitle\tcompany\tstatus\n",
                encoding="utf-8",
            )

        lines = "\n".join(
            f"{o.url}\t{date}\t{o.source}\t{o.title}\t{o.company}\tadded"
            for o in offers
        )

        with open(SCAN_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(lines + "\n")

    def _print_summary(self, result: ScanResult, dry_run: bool):
        """Print a formatted scan summary."""
        sep = "=" * 45
        print(f"\n{sep}")
        print(f"Portal Scan -- {result.date}")
        print(sep)
        print(f"Companies scanned:     {result.companies_scanned}")
        print(f"Total jobs found:      {result.total_found}")
        print(f"Filtered by title:     {result.filtered_by_title} removed")
        print(f"Duplicates:            {result.duplicates} skipped")
        print(f"New offers added:      {len(result.new_offers)}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for e in result.errors:
                print(f"  [X] {e['company']}: {e['error']}")

        if result.new_offers:
            print("\nNew offers:")
            for o in result.new_offers:
                print(f"  + {o.company} | {o.title} | {o.location or 'N/A'}")
            if dry_run:
                print("\n(dry run — run without --dry-run to save results)")
            else:
                print(f"\nResults saved to pipeline.md and scan_history.tsv")

        print(f"\n-> Run 'python -m agents.cli score <URL>' to evaluate offers.")
