"""3pm run: Trade and lifestyle businesses."""
import json
from scraper import scrape_maps
from email_finder import find_email
from emailer import send_email
from sheets import get_or_create_sheet, get_existing_names, append_lead

with open("saved_config.json") as f:
    cfg = json.load(f)
PASSWORD = cfg["gmail_password"]
FROM_EMAIL = "oluwadameelola@gmail.com"

SHEET = "AI Automation Leads"
CREDENTIALS = "credentials.json"

SEARCHES = [
    ("car dealership", "Phoenix, USA"),
    ("car dealership", "Calgary, Canada"),
    ("car dealership", "Manchester, UK"),
    ("car dealership", "Las Vegas, USA"),
    ("car dealership", "Edmonton, Canada"),
    ("car dealership", "Leeds, UK"),
    ("property management", "Denver, USA"),
    ("property management", "Auckland, New Zealand"),
    ("property management", "Glasgow, Scotland"),
    ("property management", "Austin, USA"),
    ("property management", "Christchurch, New Zealand"),
    ("property management", "Edinburgh, Scotland"),
    ("driving school", "Birmingham, UK"),
    ("driving school", "Dublin, Ireland"),
    ("driving school", "Brisbane, Australia"),
    ("driving school", "Leeds, UK"),
    ("driving school", "Cork, Ireland"),
    ("driving school", "Adelaide, Australia"),
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

print("\n[done] 3pm run complete.")
