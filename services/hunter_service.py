import os
import requests
from dotenv import load_dotenv

load_dotenv()

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
HUNTER_BASE_URL = "https://api.hunter.io/v2"


def search_emails(domain: str, company_name: str = None) -> list[dict]:
    """Search Hunter.io for emails at a given domain."""
    if not HUNTER_API_KEY:
        return []

    params = {
        "domain": domain,
        "api_key": HUNTER_API_KEY,
        "limit": 10,
    }
    if company_name:
        params["company"] = company_name

    try:
        resp = requests.get(f"{HUNTER_BASE_URL}/domain-search", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        contacts = []
        for person in data.get("emails", []):
            email = person.get("value", "")
            if not email:
                continue
            contacts.append({
                "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                "email": email,
                "title": person.get("position", ""),
                "linkedin_url": person.get("linkedin", ""),
                "source": "hunter",
            })
        return contacts
    except Exception as e:
        print(f"[Hunter] Error: {e}")
        return []


def find_email(first_name: str, last_name: str, domain: str) -> dict | None:
    """Find a specific person's email using Hunter Email Finder."""
    if not HUNTER_API_KEY:
        return None

    params = {
        "first_name": first_name,
        "last_name": last_name,
        "domain": domain,
        "api_key": HUNTER_API_KEY,
    }

    try:
        resp = requests.get(f"{HUNTER_BASE_URL}/email-finder", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        email = data.get("email", "")
        if not email:
            return None
        return {
            "name": f"{first_name} {last_name}".strip(),
            "email": email,
            "title": "",
            "linkedin_url": "",
            "source": "hunter",
        }
    except Exception as e:
        print(f"[Hunter] Email finder error: {e}")
        return None


def verify_email(email: str) -> bool:
    """Verify if an email address is valid using Hunter."""
    if not HUNTER_API_KEY:
        return True  # assume valid if no key

    params = {"email": email, "api_key": HUNTER_API_KEY}

    try:
        resp = requests.get(f"{HUNTER_BASE_URL}/email-verifier", params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json().get("data", {})
        status = result.get("status", "")
        return status in ("valid", "accept_all", "webmail")
    except Exception as e:
        print(f"[Hunter] Verify error: {e}")
        return True
