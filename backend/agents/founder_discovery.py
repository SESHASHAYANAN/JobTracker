"""Founder Discovery Agent — combines multiple sources for founder profiles."""
from __future__ import annotations
from models import Job, Founder
from services.antiblock import safe_get
from bs4 import BeautifulSoup


async def discover_founders(jobs: list[Job]) -> list[Job]:
    """Enrich jobs with founder data from company /about and /team pages."""
    # Only try for jobs missing founders
    to_enrich = [j for j in jobs if not j.founders and j.company_website][:25]

    for job in to_enrich:
        website = job.company_website or ""
        if not website:
            continue
        website = website.rstrip("/")
        if not website.startswith("http"):
            website = f"https://{website}"

        founders = []
        # Try /about and /team pages
        for path in ["/about", "/team", "/about-us"]:
            try:
                html = await safe_get(f"{website}{path}", timeout=12)
                if not html:
                    continue
                soup = BeautifulSoup(html, "html.parser")

                # Look for team/people sections
                people_sections = soup.find_all(
                    ["div", "section"],
                    class_=lambda c: c and any(k in c.lower() for k in ["team", "people", "founder", "leadership"])
                )
                if not people_sections:
                    people_sections = [soup]

                for section in people_sections[:3]:
                    # Look for name + title patterns
                    cards = section.find_all(["div", "li", "article"], limit=10)
                    for card in cards:
                        name_el = card.find(["h2", "h3", "h4", "strong", "p"], class_=lambda c: c and "name" in (c or "").lower())
                        title_el = card.find(["p", "span", "div"], class_=lambda c: c and "title" in (c or "").lower() or "role" in (c or "").lower())
                        if not name_el:
                            # try first h3/h4 as name
                            name_el = card.find(["h3", "h4"])
                        if not name_el:
                            continue
                        name = name_el.get_text(strip=True)
                        title = title_el.get_text(strip=True) if title_el else ""

                        if not name or len(name) < 2 or len(name) > 50:
                            continue

                        # Look for social links
                        linkedin = ""
                        twitter = ""
                        email = ""
                        for a in card.find_all("a", href=True):
                            href = a["href"]
                            if "linkedin.com" in href:
                                linkedin = href
                            elif "twitter.com" in href or "x.com" in href:
                                twitter = href
                            elif "mailto:" in href:
                                email = href.replace("mailto:", "")

                        founders.append(Founder(
                            name=name,
                            title=title or "Team Member",
                            linkedin=linkedin,
                            twitter=twitter,
                            email=email,
                            source="company_about",
                        ))

                if founders:
                    break
            except Exception:
                continue

        # Prioritise CEO/CTO/Chief of Staff first
        priority_titles = ["ceo", "cto", "chief of staff", "founder", "co-founder"]
        founders.sort(
            key=lambda f: next(
                (i for i, t in enumerate(priority_titles) if t in f.title.lower()),
                len(priority_titles),
            )
        )
        job.founders = founders[:5]  # max 5 founders

    return jobs
