"""Groq service — cold DM generation using LLaMA 3."""
from __future__ import annotations
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))


async def generate_cold_dm(
    company_name: str,
    role_title: str,
    founder_name: str = "the hiring manager",
    candidate_profile: str | None = None,
) -> str:
    profile_block = ""
    if candidate_profile:
        profile_block = f"\nCandidate info: {candidate_profile}"
    try:
        resp = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write short, warm, personalised cold outreach DMs to startup founders. "
                        "Keep it to exactly 3 lines. Neutral professional tone. No emojis. "
                        "Mention the company and role naturally."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Write a 3-line cold DM to {founder_name} at {company_name} "
                        f"about the {role_title} role.{profile_block}"
                    ),
                },
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq] cold DM error: {e}")
        return f"Hi {founder_name}, I'm interested in the {role_title} role at {company_name}. Would love to connect and learn more about the opportunity."


async def generate_cold_email(
    company_name: str,
    role_title: str,
    founder_name: str = "the hiring manager",
    resume_text: str = "",
    job_description: str = "",
) -> str:
    """Generate a personalised cold email based on resume + job description."""
    try:
        resp = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write personalised, compelling cold outreach emails to startup founders/hiring managers. "
                        "The email should be 5-8 sentences. Professional but warm tone. No emojis. "
                        "Reference specific skills from the candidate's resume that align with the job. "
                        "Include a clear subject line at the top prefixed with 'Subject: '. "
                        "End with a soft call-to-action asking for a brief call or coffee chat."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Write a cold email to {founder_name} at {company_name} "
                        f"about the {role_title} role.\n\n"
                        f"Candidate Resume Summary:\n{resume_text[:2000]}\n\n"
                        f"Job Description:\n{job_description[:1000]}"
                    ),
                },
            ],
            max_tokens=500,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[groq] cold email error: {e}")
        return (
            f"Subject: Interest in {role_title} at {company_name}\n\n"
            f"Hi {founder_name},\n\n"
            f"I came across the {role_title} position at {company_name} and was excited by the opportunity. "
            f"Based on my background and experience, I believe I could make a meaningful contribution to your team. "
            f"I'd love the chance to discuss how my skills align with what you're building.\n\n"
            f"Would you be open to a brief call this week?\n\n"
            f"Best regards"
        )
