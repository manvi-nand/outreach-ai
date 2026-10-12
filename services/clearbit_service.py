import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLEARBIT_API_KEY = os.getenv("CLEARBIT_API_KEY", "")


def get_company_info(company_name: str, domain: str = None) -> dict:
    """Fetch company details from Clearbit. Falls back to name-based lookup."""
    if not CLEARBIT_API_KEY:
        return {}

    headers = {"Authorization": f"Bearer {CLEARBIT_API_KEY}"}

    # Try domain lookup first (more accurate)
    if domain:
        try:
            resp = requests.get(
                f"https://company.clearbit.com/v2/companies/find",
                params={"domain": domain},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                return _parse_clearbit(resp.json())
        except Exception as e:
            print(f"[Clearbit] Domain lookup error: {e}")

    # Fall back to name-based lookup
    try:
        resp = requests.get(
            "https://company.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            best = results[0]
            # Do a full lookup with the domain we got
            domain_found = best.get("domain", "")
            if domain_found:
                full_resp = requests.get(
                    "https://company.clearbit.com/v2/companies/find",
                    params={"domain": domain_found},
                    headers=headers,
                    timeout=15,
                )
                if full_resp.status_code == 200:
                    return _parse_clearbit(full_resp.json())
            return {
                "name": best.get("name", company_name),
                "domain": domain_found,
                "description": "",
                "industry": "",
                "size": "",
                "website": f"https://{domain_found}" if domain_found else "",
                "linkedin_url": "",
            }
    except Exception as e:
        print(f"[Clearbit] Name lookup error: {e}")

    return {}


def _parse_clearbit(data: dict) -> dict:
    metrics = data.get("metrics", {})
    size_range = metrics.get("employeesRange", "") or str(metrics.get("employees", ""))
    return {
        "name": data.get("name", ""),
        "domain": data.get("domain", ""),
        "description": data.get("description", ""),
        "industry": data.get("category", {}).get("industry", ""),
        "size": size_range,
        "website": data.get("url", ""),
        "linkedin_url": data.get("linkedin", {}).get("handle", ""),
    }
