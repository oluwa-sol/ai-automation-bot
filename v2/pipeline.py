"""Find, research and draft leads into the review queue. Sends nothing.

Usage (from the repo root):
    python -m v2.pipeline                 # all searches in config
    python -m v2.pipeline --niche "med spa" --limit 5
"""

import argparse
from datetime import date
from urllib.parse import urlparse

from email_finder import find_email
from scraper import scrape_maps
from v2 import config
from v2.draft import draft, greeting
from v2.enrich import enrich
from v2.qualify import score
from v2.queue import COL, append_rows, known_businesses, open_queue


def run(niches: list[str], limit: int):
    ws = open_queue(config.SHEET_NAME, config.QUEUE_TAB)
    seen = known_businesses(ws, config.LEGACY_SHEETS)
    seen_emails = {e.strip().lower() for e in ws.col_values(COL["Email"])[1:] if e.strip()}
    queued = 0

    for niche in niches:
        for category, location in config.SEARCHES[niche]:
            if queued >= limit:
                break
            print(f"\n[*] {niche}: {category} / {location}")
            try:
                listings = scrape_maps(category, location, config.LISTINGS_PER_SEARCH)
            except Exception as e:
                print(f"  [!] scrape failed: {e}")
                continue

            for lead in listings:
                if queued >= limit:
                    break
                if lead["name"].strip().lower() in seen:
                    print(f"  [skip] already contacted: {lead['name']}")
                    continue
                seen.add(lead["name"].strip().lower())
                try:
                    row = process(lead, niche, location, seen_emails)
                except Exception as e:  # one bad website must not cost the whole batch
                    print(f"  [!] {lead['name']}: {type(e).__name__}: {e}")
                    continue
                if row:
                    append_rows(ws, [row])  # saved straight away, so a later crash loses nothing
                    queued += 1
                    print(f"  [+] queued ({row['Score']}): {lead['name']}")

    print(f"\n[done] {queued} leads added to '{config.QUEUE_TAB}' for review.")


def web_email(lead: dict) -> str:
    """Search the web for the business's email when its site shows none.

    Only accepted on the business's own domain, so we never email a different
    company that happened to appear in the search results.
    """
    domain = urlparse(lead.get("website", "")).netloc.lower().removeprefix("www.")
    if not domain:
        return ""
    # Website passes already ran in enrich(), so skip straight to search.
    email = find_email(lead["name"], lead["location"], "")
    return email if email and email.lower().endswith("@" + domain) else ""


def process(lead: dict, niche: str, location: str, seen_emails: set) -> dict | None:
    """Research, score and draft one lead. Returns a queue row, or None to skip it."""
    lead = enrich(lead)
    if not lead["site_emails"]:
        found = web_email(lead)
        if not found:
            print(f"  [skip] no email found: {lead['name']}")
            return None
        lead["site_emails"] = [found]
        lead["email_source"] = "web search"
    # Chains and franchises share one inbox across locations. Pitch each once.
    if lead["site_emails"][0].lower() in seen_emails:
        print(f"  [skip] same inbox as an earlier lead (chain): {lead['name']}")
        return None
    seen_emails.add(lead["site_emails"][0].lower())

    points, hook, reasons = score(lead, niche)
    if not hook or points < config.MIN_SCORE_TO_QUEUE:
        print(f"  [skip] score {points}, hook '{hook}': {lead['name']}")
        return None

    d = draft(lead, niche, hook)
    return {
        "Status": "REVIEW", "Score": points, "Niche": niche,
        "Business": lead["name"], "City": location, "Website": lead["website"],
        "Reviews": lead.get("reviews", ""),
        "Contact": f"{lead['contact_name']} ({lead['contact_title']})".strip(" ()"),
        "Email": lead["site_emails"][0], "Hook (verify on site)": hook,
        "Notes": "email from web search, check it before approving" if lead.get("email_source") else "",
        "Why it scored": "; ".join(reasons), "Subject": d["subject"],
        "Body": f"{greeting(lead)}\n\n{d['body']}" if d["body"] else "",
        "Draft issues": "; ".join(d["problems"]), "Date Added": str(date.today()),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--niche", choices=list(config.SEARCHES), help="one niche only")
    p.add_argument("--limit", type=int, default=config.MAX_QUEUED_PER_RUN)
    a = p.parse_args()
    run([a.niche] if a.niche else list(config.SEARCHES), a.limit)
