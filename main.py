"""
Usage:
  python main.py --category "dental clinic" --location "Warsaw, Poland"
  python main.py --category "hair salon" --location "Calgary, Canada" --sheet "AI Automation Leads"
"""
import argparse
import json
from scraper import scrape_maps
from email_finder import find_email
from emailer import send_email
from sheets import get_or_create_sheet, get_existing_names, append_lead

parser = argparse.ArgumentParser()
parser.add_argument("--category", required=True)
parser.add_argument("--location", required=True)
parser.add_argument("--sheet", default="AI Automation Leads")
parser.add_argument("--credentials", default="credentials.json")
parser.add_argument("--max", type=int, default=50)
args = parser.parse_args()

with open("saved_config.json") as f:
    PASSWORD = json.load(f)["gmail_password"]

print(f"\n[*] Scraping: {args.category} in {args.location}")
sheet = get_or_create_sheet(args.sheet, args.credentials)
existing = get_existing_names(sheet)

leads = scrape_maps(args.category, args.location, args.max)
print(f"\n[*] Found {len(leads)} leads without automation signals\n")

saved = 0
for lead in leads:
    name = lead["name"]
    print(f"[>] {name}")
    email = find_email(name, args.location, lead.get("website", ""))
    if not email:
        print(f"  [skip] No email found")
        continue
    lead["email"] = email
    if append_lead(sheet, lead, existing):
        send_email(email, name, args.category, args.location, PASSWORD)
        saved += 1

print(f"\n[done] {saved} leads saved and emailed.")
