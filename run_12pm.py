"""12pm run: Finance and legal services."""
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
    ("insurance broker", "Toronto, Canada"),
    ("insurance broker", "Melbourne, Australia"),
    ("insurance broker", "Cape Town, South Africa"),
    ("accounting firm", "Dublin, Ireland"),
    ("accounting firm", "Auckland, New Zealand"),
    ("accounting firm", "Calgary, Canada"),
    ("law firm", "Sydney, Australia"),
    ("law firm", "Vancouver, Canada"),
    ("law firm", "Edinburgh, Scotland"),
    ("real estate agent", "Ottawa, Canada"),
    ("real estate agent", "Perth, Australia"),
    ("real estate agent", "Dublin, Ireland"),
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
