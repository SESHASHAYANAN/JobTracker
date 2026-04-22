"""Resume Parser — extracts text from uploaded PDF resumes + AI-powered parsing."""
from __future__ import annotations
import io
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()


def _get_groq_client():
    """Lazy-load Groq client to avoid import errors if not installed."""
    try:
        from groq import Groq
        return Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    except ImportError:
        return None


async def ai_parse_resume(resume_text: str) -> dict:
    """Use Groq (fast inference) to extract structured profile data from resume text.

    Returns:
    {
        skills: [str], experience_years: int, education: [str],
        job_titles: [str], industries: [str], certifications: [str],
        tools: [str], experience_level: str, role_preferences: [str],
        summary: str
    }
    """
    client = _get_groq_client()
    if not client:
        # Fallback to keyword-based extraction
        return {
            "skills": extract_skills(resume_text),
            "experience_years": 0,
            "education": [],
            "job_titles": [],
            "industries": [],
            "certifications": [],
            "tools": [],
            "experience_level": extract_experience_level(resume_text),
            "role_preferences": extract_role_preferences(resume_text),
            "summary": "",
        }

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise resume parser. Extract structured data from the resume text. "
                        "Respond with ONLY valid JSON, no markdown fences. Keys: "
                        "skills (array of technical skills), "
                        "experience_years (integer), "
                        "education (array of degree strings), "
                        "job_titles (array of past/current titles), "
                        "industries (array of industry domains), "
                        "certifications (array of certification names), "
                        "tools (array of tools/platforms used), "
                        "experience_level (one of: Intern, New Grad, Mid, Senior, Staff, Principal), "
                        "role_preferences (array of role categories like Frontend, Backend, ML/AI, DevOps), "
                        "summary (2-sentence professional summary)."
                    ),
                },
                {"role": "user", "content": f"Parse this resume:\n\n{resume_text[:4000]}"},
            ],
            max_tokens=800,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        result = json.loads(raw)

        # Ensure all expected keys exist
        result.setdefault("skills", [])
        result.setdefault("experience_years", 0)
        result.setdefault("education", [])
        result.setdefault("job_titles", [])
        result.setdefault("industries", [])
        result.setdefault("certifications", [])
        result.setdefault("tools", [])
        result.setdefault("experience_level", "New Grad")
        result.setdefault("role_preferences", ["Engineering"])
        result.setdefault("summary", "")

        return result

    except Exception as e:
        print(f"[resume_parser] AI parse error (falling back to keywords): {e}")
        return {
            "skills": extract_skills(resume_text),
            "experience_years": 0,
            "education": [],
            "job_titles": [],
            "industries": [],
            "certifications": [],
            "tools": [],
            "experience_level": extract_experience_level(resume_text),
            "role_preferences": extract_role_preferences(resume_text),
            "summary": "",
        }


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)
    except ImportError:
        # Fallback: try PyPDF2
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)
        except ImportError:
            return ""


def extract_skills(text: str) -> list[str]:
    """Extract technical skills from resume text."""
    skill_keywords = [
        # Programming Languages
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "elixir",
        # Frontend
        "react", "vue", "angular", "svelte", "next.js", "nextjs", "nuxt",
        "html", "css", "sass", "tailwind", "webpack", "vite", "redux",
        "graphql", "rest api", "framer motion",
        # Backend
        "node.js", "nodejs", "express", "django", "flask", "fastapi", "spring",
        "rails", "laravel", "gin", "fiber", "actix",
        # Databases
        "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
        "dynamodb", "cassandra", "sqlite", "supabase", "firebase",
        # Cloud / DevOps
        "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform",
        "jenkins", "ci/cd", "github actions", "ansible", "pulumi",
        # AI / ML
        "machine learning", "deep learning", "nlp", "computer vision",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "llm", "transformers", "hugging face", "openai", "langchain",
        "rag", "fine-tuning", "reinforcement learning",
        # Mobile
        "react native", "flutter", "ios", "android", "swiftui",
        "jetpack compose", "expo",
        # Blockchain
        "solidity", "ethereum", "web3", "smart contracts", "defi",
        # Data
        "sql", "spark", "airflow", "dbt", "snowflake", "bigquery",
        "data engineering", "data science", "analytics",
        # Security
        "cybersecurity", "penetration testing", "soc", "siem",
        "vulnerability", "encryption",
        # Other
        "agile", "scrum", "product management", "figma", "design systems",
    ]

    text_lower = text.lower()
    found = []
    for skill in skill_keywords:
        if skill in text_lower:
            found.append(skill)
    return found


def extract_experience_level(text: str) -> str:
    """Infer experience level from resume text."""
    text_lower = text.lower()

    # Check for fresher/new grad signals FIRST (higher priority)
    fresher_signals = [
        "fresher", "fresh graduate", "new grad", "new graduate", "recent graduate",
        "entry level", "entry-level", "intern", "internship", "campus placement",
        "b.tech", "btech", "b.e.", "b.sc", "bsc", "bachelor", "undergraduate",
        "freshman", "sophomore", "final year", "penultimate year",
        "college project", "university project", "academic project",
        "0 years", "no experience", "seeking first", "aspiring",
        "looking for my first", "career start", "just graduated",
    ]
    for s in fresher_signals:
        if s in text_lower:
            return "New Grad"

    # Extract years of experience
    year_matches = re.findall(r'(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)', text_lower)
    if year_matches:
        max_years = max(int(y) for y in year_matches)
        if max_years >= 7:
            return "Senior"
        elif max_years >= 3:
            return "Mid"
        else:
            return "New Grad"

    # Check for senior signals — require context (e.g., "senior engineer" not just "senior" alone)
    senior_title_signals = [
        "senior software", "senior engineer", "senior developer", "senior data",
        "lead engineer", "lead developer", "tech lead", "principal engineer",
        "staff engineer", "architect", "engineering director", "vp of engineering",
        "head of engineering", "cto",
    ]
    for s in senior_title_signals:
        if s in text_lower:
            return "Senior"

    # Default: if no clear signals found, assume new grad / fresher
    # (most resumes uploaded by experienced professionals will mention years of experience)
    return "New Grad"


def extract_role_preferences(text: str) -> list[str]:
    """Extract likely role categories from resume."""
    text_lower = text.lower()
    categories = []

    role_map = {
        "Frontend": ["react", "vue", "angular", "frontend", "front-end", "css", "html", "ui engineer", "web developer"],
        "Backend": ["backend", "back-end", "server", "api", "microservices", "django", "flask", "fastapi", "spring", "node.js"],
        "AI/ML": ["machine learning", "deep learning", "nlp", "computer vision", "ml engineer", "data scientist", "pytorch", "tensorflow", "llm"],
        "DevOps": ["devops", "sre", "site reliability", "infrastructure", "kubernetes", "docker", "terraform", "ci/cd", "platform engineer"],
        "Mobile": ["ios", "android", "react native", "flutter", "mobile", "swift", "kotlin"],
        "Data": ["data engineer", "data analyst", "analytics", "sql", "etl", "pipeline", "warehouse", "spark"],
        "Design": ["design", "figma", "ux", "ui/ux", "product design", "user research"],
        "Cybersecurity": ["security", "cybersecurity", "penetration", "soc", "vulnerability", "encryption", "devsecops"],
        "Blockchain": ["blockchain", "web3", "solidity", "ethereum", "smart contract", "defi", "crypto"],
        "Engineering": ["software engineer", "full stack", "full-stack", "programmer", "developer"],
        "GTM": ["product manager", "growth", "marketing", "sales", "account executive", "business development"],
        "Ops": ["operations", "compliance", "program manager", "project manager"],
    }

    for category, keywords in role_map.items():
        for kw in keywords:
            if kw in text_lower:
                if category not in categories:
                    categories.append(category)
                break

    return categories if categories else ["Engineering"]
