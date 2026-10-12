import os
import requests
from dotenv import load_dotenv

load_dotenv()

SNOV_CLIENT_ID = os.getenv("SNOV_CLIENT_ID", "")
SNOV_CLIENT_SECRET = os.getenv("SNOV_CLIENT_SECRET", "")
SNOV_BASE_URL = "https://api.snov.io/v1"

_snov_token = None


def _get_token() -> str | None:
    global _snov_token
    if _snov_token:
        return _snov_token
    if not SNOV_CLIENT_ID or not SNOV_CLIENT_SECRET:
        return None
    try:
        resp = requests.post(
            "https://api.snov.io/v1/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": SNOV_CLIENT_ID,
                "client_secret": SNOV_CLIENT_SECRET,
            },
            timeout=15,
        )
        resp.raise_for_status()
        _snov_token = resp.json().get("access_token")
        return _snov_token
    except Exception as e:
        print(f"[Snov] Auth error: {e}")
        return None


def search_emails(domain: str) -> list[dict]:
    """Search Snov.io for emails at a given domain."""
    token = _get_token()
    if not token:
        return []

    try:
        resp = requests.post(
            f"{SNOV_BASE_URL}/get-emails-from-url",
            data={"access_token": token, "url": domain, "type": "all", "limit": 10},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        contacts = []
        for person in data.get("emails", []):
            email = person.get("email", "")
            if not email:
                continue
            contacts.append({
                "name": f"{person.get('firstName', '')} {person.get('lastName', '')}".strip(),
                "email": email,
                "title": person.get("position", ""),
                "linkedin_url": "",
                "source": "snov",
            })
        return contacts
    except Exception as e:
        print(f"[Snov] Search error: {e}")
        return []


def verify_email(email: str) -> bool:
    """Verify an email address via Snov.io."""
    token = _get_token()
    if not token:
        return True

    try:
        add_resp = requests.post(
            f"{SNOV_BASE_URL}/add-emails-to-verify",
            data={"access_token": token, "emails[]": email},
            timeout=15,
        )
        add_resp.raise_for_status()

        result_resp = requests.post(
            f"{SNOV_BASE_URL}/get-emails-verification-result",
            data={"access_token": token, "emails[]": email},
            timeout=15,
        )
        result_resp.raise_for_status()
        results = result_resp.json()
        status = results.get(email, {}).get("status", "")
        return status in ("valid", "accept_all")
    except Exception as e:
        print(f"[Snov] Verify error: {e}")
        return True
