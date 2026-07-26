"""8am run: Healthcare and professional services."""
import json
from scraper import scrape_maps
from email_finder import find_email
from emailer import send_email
from sheets import get_or_create_sheet, get_existing_names, append_lead

with open("saved_config.json") as f:
    PASSWORD = json.load(f)["gmail_password"]

SHEET = "AI Automation Leads"
CREDENTIALS = "credentials.json"

SEARCHES = [
    ("dental clinic", "Calgary, Canada"),
    ("dental clinic", "Brisbane, Australia"),
    ("dental clinic", "Dublin, Ireland"),
    ("mortgage broker", "Toronto, Canada"),
    ("mortgage broker", "Melbourne, Australia"),
    ("mortgage broker", "Auckland, New Zealand"),
    ("vet clinic", "Ottawa, Canada"),
    ("vet clinic", "Perth, Australia"),
    ("vet clinic", "Edinburgh, Scotland"),
    ("immigration consultant", "London, UK"),
    ("immigration consultant", "Sydney, Australia"),
    ("immigration consultant", "Vancouver, Canada"),
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
            send_email(email, lead["name"], category, location, PASSWORD)


for cat, loc in SEARCHES:
    try:
        run(cat, loc)
    except Exception as e:
        print(f"  [!] Failed {cat} / {loc}: {e}")

print("\n[done] 8am run complete.")
