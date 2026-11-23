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
from v2.gap import find_gap, hook_text
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

            # Research every listing once, so each lead can be compared with its competitors.
            researched = research_all(listings) if config.USE_COMPETITOR_GAPS else {}
            for lead in listings:
                if queued >= limit:
                    break
                if lead["name"].strip().lower() in seen:
                    print(f"  [skip] already contacted: {lead['name']}")
                    continue
                seen.add(lead["name"].strip().lower())
                try:
                    row = process(lead, niche, location, seen_emails, researched)
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


def research_all(listings: list[dict]) -> dict:
    """Enrich every listing in a search. Returns {name: enriched lead}."""
    out = {}
    for l in listings:
        try:
            out[l["name"]] = enrich(l)
        except Exception as e:
            print(f"  [!] research failed for {l['name']}: {e}")
    return out


def process(lead: dict, niche: str, location: str, seen_emails: set, researched: dict | None = None) -> dict | None:
    """Research, score and draft one lead. Returns a queue row, or None to skip it."""
    researched = researched or {}
    lead = researched.get(lead["name"]) or enrich(lead)
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
    gap = find_gap(lead, list(researched.values())) if researched else None
    if gap:  # a verified competitor gap is the strongest hook we have
        hook = hook_text(gap, lead["name"])
        points += 3
        reasons.append(f"{gap['competitor_count']} nearby competitor(s) have it, they don't")
    if not hook or points < config.MIN_SCORE_TO_QUEUE:
        print(f"  [skip] score {points}, hook '{hook}': {lead['name']}")
        return None

    d = draft(lead, niche, hook, gap)
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


def regap(redo: bool = False):
    """Redraft leads still waiting in REVIEW around a competitor gap from their own search.
    redo=True also redrafts rows that already have a gap hook (after rule changes)."""
    from v2.queue import rows_with_status, update
    ws = open_queue(config.SHEET_NAME, config.QUEUE_TAB)
    rows = [r for r in rows_with_status(ws, "REVIEW") if redo or not r["Hook (verify on site)"].startswith("gap:")]
    all_searches = {**config.SEARCHES, **config.PAUSED_SEARCHES}
    for r in rows:
        search = next((s for s in all_searches.get(r["Niche"], []) if s[1] == r["City"]), None)
        if not search:
            print(f"  [regap] no search for {r['Niche']} / {r['City']}: {r['Business']}")
            continue
        listings = scrape_maps(search[0], search[1], config.LISTINGS_PER_SEARCH)
        researched = research_all(listings)
        lead = researched.get(r["Business"]) or enrich({"name": r["Business"], "website": r["Website"],
                                                        "location": r["City"], "reviews": r["Reviews"]})
        lead.setdefault("location", r["City"])
        gap = find_gap(lead, list(researched.values()))
        if not gap:
            update(ws, r["_row"], **{"Draft issues": "regap: no competitor gap found, kept old draft"})
            print(f"  [regap] no gap: {r['Business']}")
            continue
        d = draft(lead, r["Niche"], "", gap)
        greet = r["Body"].split(chr(10), 1)[0] if r["Body"] else "Hi there,"
        update(ws, r["_row"], Subject=d["subject"] or r["Subject"], Body=greet + chr(10) * 2 + d["body"],
               **{"Hook (verify on site)": hook_text(gap, r["Business"]), "Draft issues": "; ".join(d["problems"])})
        print(f"  [regap] {r['Business']}: vs {gap['competitor']} ({gap['feature']})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--niche", choices=list(config.SEARCHES), help="one niche only")
    p.add_argument("--regap", action="store_true", help="redraft REVIEW rows around a competitor gap")
    p.add_argument("--redo", action="store_true", help="with --regap: redo rows that already have a gap")
    p.add_argument("--limit", type=int, default=config.MAX_QUEUED_PER_RUN)
    a = p.parse_args()
    if a.regap:
        regap(a.redo)
    else:
        run([a.niche] if a.niche else list(config.SEARCHES), a.limit)
