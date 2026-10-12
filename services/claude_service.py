import os
import json
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

def _get_client():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF resume."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def parse_resume(raw_text: str) -> dict:
    """Use OpenAI to parse a resume into structured data."""
    client = _get_client()
    if not client:
        return {"name": "", "skills": [], "experience": [], "target_roles": []}

    prompt = f"""You are a resume parser. Extract the following from this resume and return ONLY valid JSON with no markdown:

{{
  "name": "candidate full name",
  "email": "candidate email if present",
  "summary": "2-3 sentence professional summary",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{
      "company": "company name",
      "title": "job title",
      "duration": "start - end",
      "highlights": ["key achievement 1", "key achievement 2"]
    }}
  ],
  "education": [
    {{
      "school": "university name",
      "degree": "degree and major",
      "year": "graduation year"
    }}
  ],
  "target_roles": ["inferred ideal job titles based on experience"]
}}

RESUME:
{raw_text}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"name": "", "skills": [], "experience": [], "target_roles": []}


def draft_initial_email(
    resume_data: dict,
    company_info: dict,
    contact: dict,
) -> dict:
    """Draft a personalized cold outreach email."""
    client = _get_client()
    if not client:
        return {
            "subject": f"Exploring opportunities at {company_info.get('name', 'your company')}",
            "body": "Please add your OpenAI API key in Settings to generate personalized emails.",
        }

    candidate_name = resume_data.get("name", "the candidate")
    skills = ", ".join(resume_data.get("skills", [])[:8])
    experience_summary = _format_experience(resume_data.get("experience", []))
    target_roles = ", ".join(resume_data.get("target_roles", []))

    contact_name = contact.get("name", "")
    contact_title = contact.get("title", "Hiring Team")
    company_name = company_info.get("name", "your company")
    company_desc = company_info.get("description", "")
    company_industry = company_info.get("industry", "")
    greeting = f"Hi {contact_name.split()[0]}," if contact_name else "Hi,"

    prompt = f"""Write a concise, personalized cold outreach email from a job seeker to a potential employer.

CANDIDATE INFO:
- Name: {candidate_name}
- Key Skills: {skills}
- Experience: {experience_summary}
- Target Roles: {target_roles}

RECIPIENT INFO:
- Name: {contact_name or 'not specified'}
- Title: {contact_title}
- Company: {company_name}
- Company Description: {company_desc}
- Industry: {company_industry}

REQUIREMENTS:
- Start with: "{greeting}"
- 3 short paragraphs max (150 words total)
- Paragraph 1: Why you're reaching out and a specific hook about the company
- Paragraph 2: 2-3 concrete highlights from your background that are relevant to them
- Paragraph 3: Simple, low-friction call to action (e.g., "Would you be open to a 15-minute call?")
- Sign off as: {candidate_name}
- NO generic phrases like "I hope this email finds you well"
- Sound human, not like a template
- Return ONLY a JSON object with keys "subject" and "body"."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"subject": f"Connecting with {company_name}", "body": raw}


def draft_followup_email(
    resume_data: dict,
    company_info: dict,
    contact: dict,
    followup_number: int,
    original_subject: str,
) -> dict:
    """Draft a follow-up email (1st or 2nd follow-up)."""
    client = _get_client()
    if not client:
        return {
            "subject": f"Re: {original_subject}",
            "body": "Please add your OpenAI API key in Settings to generate follow-up emails.",
        }

    candidate_name = resume_data.get("name", "the candidate")
    contact_name = contact.get("name", "")
    company_name = company_info.get("name", "your company")
    greeting = f"Hi {contact_name.split()[0]}," if contact_name else "Hi,"
    tone = "friendly and brief" if followup_number == 1 else "very short and final"
    note = (
        "This is a first follow-up sent 5 days after the initial email."
        if followup_number == 1
        else "This is the final follow-up. Keep it very short — 2-3 sentences max."
    )

    prompt = f"""Write a {tone} follow-up email.

{note}

CONTEXT:
- Candidate: {candidate_name}
- Company: {company_name}
- Recipient: {contact_name or 'not specified'}
- Original email subject: {original_subject}
- Follow-up number: {followup_number}

REQUIREMENTS:
- Start with: "{greeting}"
- Reference the previous email naturally
- Add a small new value or observation (don't just say "following up")
- End with a simple CTA or graceful close (for #2: "No worries if the timing isn't right")
- Sign off as: {candidate_name}
- Return ONLY JSON with keys "subject" and "body"."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"subject": f"Re: {original_subject}", "body": raw}


def _format_experience(experience: list) -> str:
    if not experience:
        return "No experience listed"
    parts = []
    for exp in experience[:3]:
        title = exp.get("title", "")
        company = exp.get("company", "")
        if title and company:
            parts.append(f"{title} at {company}")
    return "; ".join(parts) if parts else "Various roles"
