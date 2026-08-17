"""8am run: Healthcare, professional services, physiotherapy."""
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
    ("dental clinic", "Calgary, Canada"),
    ("dental clinic", "Brisbane, Australia"),
    ("dental clinic", "Dublin, Ireland"),
    ("dental clinic", "Edmonton, Canada"),
    ("dental clinic", "Adelaide, Australia"),
    ("dental clinic", "Cork, Ireland"),
    ("mortgage broker", "Toronto, Canada"),
    ("mortgage broker", "Melbourne, Australia"),
    ("mortgage broker", "Auckland, New Zealand"),
    ("mortgage broker", "Winnipeg, Canada"),
    ("mortgage broker", "Christchurch, New Zealand"),
    ("mortgage broker", "Birmingham, UK"),
    ("vet clinic", "Ottawa, Canada"),
    ("vet clinic", "Perth, Australia"),
    ("vet clinic", "Edinburgh, Scotland"),
    ("vet clinic", "Hamilton, Canada"),
    ("vet clinic", "Canberra, Australia"),
    ("vet clinic", "Glasgow, Scotland"),
    ("physiotherapy clinic", "Melbourne, Australia"),
    ("physiotherapy clinic", "Dublin, Ireland"),
    ("physiotherapy clinic", "Edinburgh, Scotland"),
    ("physiotherapy clinic", "Auckland, New Zealand"),
    ("physical therapy", "London, UK"),
    ("physical therapy", "Dublin, Ireland"),
    ("physical therapy", "Melbourne, Australia"),
    ("physical therapy", "Toronto, Canada"),
    ("occupational therapy", "London, UK"),
    ("occupational therapy", "Dublin, Ireland"),
    ("occupational therapy", "Melbourne, Australia"),
    ("occupational therapy", "Toronto, Canada"),
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

print("\n[done] 8am run complete.")
