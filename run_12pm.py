"""12pm run: HVAC / home services."""
import json
from scraper import scrape_maps
from email_finder import find_email
from emailer import send_email
from sheets import get_or_create_sheet, get_existing_names, append_lead

with open("saved_config.json") as f:
    cfg = json.load(f)
PASSWORD = cfg["gmail_password_2"]
FROM_EMAIL = "bamee221@gmail.com"

SHEET = "AI Automation Leads"
CREDENTIALS = "credentials.json"

SEARCHES = [
    ("hvac company", "London, UK"),
    ("hvac company", "Dublin, Ireland"),
    ("hvac company", "Melbourne, Australia"),
    ("hvac company", "Toronto, Canada"),
    ("hvac company", "Sydney, Australia"),
    ("hvac company", "Edinburgh, Scotland"),
    ("plumbing company", "London, UK"),
    ("plumbing company", "Dublin, Ireland"),
    ("plumbing company", "Melbourne, Australia"),
    ("plumbing company", "Toronto, Canada"),
    ("plumbing company", "Auckland, New Zealand"),
    ("plumbing company", "Manchester, UK"),
]


def run(category, location):
    print(f"\n[*] {category} — {location}")
    sheet = get_or_create_sheet(SHEET, CREDENTIALS)
    existing = get_existing_names(sheet)
    leads = scrape_maps(category, location)
    print(f"  Found {len(leads)} candidates")
    for lead in leads:
        email = find_email(lead["name"], location, lead.get("website", ""))
        if not email:
            continue
        lead["email"] = email
        if append_lead(sheet, lead, existing):
            send_email(email, lead["name"], category, location, PASSWORD, FROM_EMAIL)


for cat, loc in SEARCHES:
    try:
        run(cat, loc)
    except Exception as e:
        print(f"  [!] Failed {cat} / {loc}: {e}")

print("\n[done] 12pm run complete.")
