import os
import requests
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
APOLLO_BASE_URL = "https://api.apollo.io/api/v1"


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "accept": "application/json",
        "X-Api-Key": APOLLO_API_KEY,
    }


def search_contacts(
    company_name: str,
    domain: str = None,
    location: str = None,
) -> list[dict]:
    """Search Apollo for contacts. Location and role filtering handled client-side."""
    if not APOLLO_API_KEY:
        return []

    # Build params list for query string (Apollo needs array params in URL)
    parts = ["per_page=25"]
    if company_name:
        parts.append(f"q_organization_name={requests.utils.quote(company_name)}")
    if domain:
        parts.append(f"q_organization_domains[]={requests.utils.quote(domain)}")
    # Pass location to Apollo if provided — client-side filter also applied as backup
    if location:
        parts.append(f"person_locations[]={requests.utils.quote(location)}")

    url = f"{APOLLO_BASE_URL}/mixed_people/api_search?{'&'.join(parts)}"

    try:
        resp = requests.post(url, headers=_headers(), timeout=15)
        if not resp.ok:
            print(f"[Apollo] Search failed ({resp.status_code}): {resp.text[:200]}")
            return []
        data = resp.json()
        return _parse_people(data.get("people", []))
    except Exception as e:
        print(f"[Apollo] search_contacts error: {e}")
        return []


def get_company_info(company_name: str) -> dict:
    """Fetch company details from Apollo."""
    if not APOLLO_API_KEY:
        return {}

    # Apollo company search uses JSON body (not query params)
    try:
        resp = requests.post(
            f"{APOLLO_BASE_URL}/mixed_companies/api_search",
            headers=_headers(),
            json={"q_organization_name": company_name, "per_page": 1},
            timeout=15,
        )
        if not resp.ok:
            print(f"[Apollo] Company fetch failed ({resp.status_code}): {resp.text[:200]}")
            return {}
        orgs = resp.json().get("organizations", [])
        if not orgs:
            return {}
        org = orgs[0]
        return {
            "name": org.get("name", company_name),
            "domain": org.get("primary_domain", ""),
            "website": org.get("website_url", ""),
            "industry": org.get("industry", ""),
            "size": str(org.get("estimated_num_employees", "")),
            "description": org.get("short_description", ""),
            "linkedin_url": org.get("linkedin_url", ""),
        }
    except Exception as e:
        print(f"[Apollo] get_company_info error: {e}")
        return {}


def _parse_people(people: list) -> list[dict]:
    contacts = []
    for person in people:
        email = person.get("email") or ""
        if not email or "@" not in email:
            continue
        city = person.get("city", "") or ""
        state = person.get("state", "") or ""
        country = person.get("country", "") or ""
        location_str = ", ".join(filter(None, [city, state, country]))
        contacts.append({
            "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
            "email": email,
            "title": person.get("title", ""),
            "linkedin_url": person.get("linkedin_url", ""),
            "location": location_str,
            "source": "apollo",
        })
    return contacts
