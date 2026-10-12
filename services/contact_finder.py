"""
Hybrid contact discovery orchestrator.
Runs Apollo + Hunter + Snov simultaneously, merges, deduplicates, filters.
"""
import os
import re
import concurrent.futures
from services import apollo_service, hunter_service, snov_service, clearbit_service


def find_company_and_contacts(
    company_name: str,
    location: str = None,
    role_filter: list[str] = None,
    manual_domain: str = None,
) -> tuple[dict, list[dict]]:
    """
    Given a company name, returns:
    - company_info dict
    - list of unique contact dicts filtered by location and role
    """
    print(f"[ContactFinder] Researching: {company_name} | Location: {location} | Roles: {role_filter}")

    # ── 1. Get company info + domain ────────────────────────────────────────
    company_info = _fetch_company_info(company_name)

    # Priority: manual override > API result > guessed
    domain = (
        manual_domain
        or company_info.get("domain", "")
        or _guess_domain(company_name)
    )
    company_info["domain"] = domain
    print(f"[ContactFinder] Domain resolved: '{domain}' {'(manual)' if manual_domain else ''}")

    # ── 2. Fetch from all sources in parallel ────────────────────────────────
    all_contacts: list[dict] = []

    def fetch_apollo():
        contacts = apollo_service.search_contacts(company_name, domain, location=location)
        print(f"[Apollo] Found {len(contacts)} contacts")
        return contacts

    def fetch_hunter():
        if not domain:
            print("[Hunter] Skipped — no domain")
            return []
        contacts = hunter_service.search_emails(domain, company_name)
        print(f"[Hunter] Found {len(contacts)} contacts")
        return contacts

    def fetch_snov():
        if not domain:
            print("[Snov] Skipped — no domain")
            return []
        contacts = snov_service.search_emails(domain)
        print(f"[Snov] Found {len(contacts)} contacts")
        return contacts

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_apollo): "apollo",
            executor.submit(fetch_hunter): "hunter",
            executor.submit(fetch_snov): "snov",
        }
        for future in concurrent.futures.as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
                all_contacts.extend(result)
            except Exception as e:
                print(f"[{source}] Thread error: {e}")

    print(f"[ContactFinder] Total raw contacts: {len(all_contacts)}")

    # ── 3. Deduplicate by email ──────────────────────────────────────────────
    seen: set[str] = set()
    unique: list[dict] = []
    for c in all_contacts:
        email = c.get("email", "").lower().strip()
        if email and email not in seen:
            seen.add(email)
            unique.append(c)
    print(f"[ContactFinder] {len(unique)} unique contacts after dedup")

    # ── 4. Client-side location filter (backup for sources without API filter) ─
    if location and unique:
        location_lower = location.lower()
        location_filtered = [
            c for c in unique
            if location_lower in (c.get("location") or "").lower()
        ]
        if location_filtered:
            unique = location_filtered
            print(f"[ContactFinder] {len(unique)} contacts after location filter")
        else:
            print(f"[ContactFinder] No location match for '{location}' — showing all")

    # ── 5. Role filter (loose fuzzy match) ───────────────────────────────────
    if role_filter:
        stopwords = {"of", "and", "the", "a", "an", "for", "in", "at", "to"}
        match_words = set()
        for kw in role_filter:
            for word in kw.lower().split():
                if word not in stopwords and len(word) > 2:
                    match_words.add(word)

        def _matches(title: str) -> bool:
            if not title:
                return False
            t = title.lower()
            return any(mw in t for mw in match_words)

        filtered = [c for c in unique if _matches(c.get("title", ""))]
        if filtered:
            unique = filtered
        else:
            print(f"[ContactFinder] No role match — showing all contacts")
        print(f"[ContactFinder] {len(unique)} contacts after role filter")

    # ── 6. Mark verification (skip API call to save credits — just flag) ──────
    for c in unique:
        c.setdefault("is_verified", True)  # assume valid; Hunter already deduped

    print(f"[ContactFinder] Final: {len(unique)} contacts")
    return company_info, unique


def _fetch_company_info(company_name: str) -> dict:
    """Try Apollo, then Clearbit for company info."""
    info = apollo_service.get_company_info(company_name)
    if info and (info.get("domain") or info.get("description")):
        return info

    if os.getenv("CLEARBIT_API_KEY"):
        clearbit_info = clearbit_service.get_company_info(company_name, domain=info.get("domain", ""))
        if clearbit_info:
            merged = {**clearbit_info, **{k: v for k, v in info.items() if v}}
            return merged

    if info:
        return info
    return {"name": company_name, "domain": "", "description": "", "industry": "", "size": "", "website": ""}


def _guess_domain(company_name: str) -> str:
    """
    Last-resort domain guesser: turns 'IBM' → 'ibm.com', 'Stripe Inc' → 'stripe.com'.
    Only used when API lookup fails entirely.
    """
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower().split()[0])
    guessed = f"{slug}.com"
    print(f"[ContactFinder] Guessed domain: {guessed}")
    return guessed
