"""Find, research and draft leads into the review queue. Sends nothing.

Usage (from the repo root):
    python -m v2.pipeline                 # all searches in config
    python -m v2.pipeline --niche "med spa" --limit 5
"""

import argparse
from datetime import date

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
    queued: list[dict] = []

    for niche in niches:
        for category, location in config.SEARCHES[niche]:
            if len(queued) >= limit:
                break
            print(f"\n[*] {niche}: {category} / {location}")
            try:
                listings = scrape_maps(category, location, config.LISTINGS_PER_SEARCH)
            except Exception as e:
                print(f"  [!] scrape failed: {e}")
                continue

            for lead in listings:
                if len(queued) >= limit:
                    break
                if lead["name"].strip().lower() in seen:
                    print(f"  [skip] already contacted: {lead['name']}")
                    continue
                seen.add(lead["name"].strip().lower())

                lead = enrich(lead)
                if not lead["site_emails"]:
                    print(f"  [skip] no email on site: {lead['name']}")
                    continue
                # Chains and franchises share one inbox across locations. Pitch each once.
                if lead["site_emails"][0].lower() in seen_emails:
                    print(f"  [skip] same inbox as an earlier lead (chain): {lead['name']}")
                    continue
                seen_emails.add(lead["site_emails"][0].lower())
                points, hook, reasons = score(lead, niche)
                if not hook or points < config.MIN_SCORE_TO_QUEUE:
                    print(f"  [skip] score {points}, hook '{hook}': {lead['name']}")
                    continue

                d = draft(lead, niche, hook)
                body = f"{greeting(lead)}\n\n{d['body']}" if d["body"] else ""
                queued.append({
                    "Status": "REVIEW", "Score": points, "Niche": niche,
                    "Business": lead["name"], "City": location, "Website": lead["website"],
                    "Reviews": lead.get("reviews", ""),
                    "Contact": f"{lead['contact_name']} ({lead['contact_title']})".strip(" ()"),
                    "Email": lead["site_emails"][0], "Hook (verify on site)": hook,
                    "Why it scored": "; ".join(reasons), "Subject": d["subject"], "Body": body,
                    "Draft issues": "; ".join(d["problems"]), "Date Added": str(date.today()),
                })
                print(f"  [+] queued ({points}): {lead['name']}")

    append_rows(ws, queued)
    print(f"\n[done] {len(queued)} leads added to '{config.QUEUE_TAB}' for review.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--niche", choices=list(config.SEARCHES), help="one niche only")
    p.add_argument("--limit", type=int, default=config.MAX_QUEUED_PER_RUN)
    a = p.parse_args()
    run([a.niche] if a.niche else list(config.SEARCHES), a.limit)
