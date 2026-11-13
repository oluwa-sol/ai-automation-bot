"""Settings for the v2 pipeline: two niches, a review queue, sending from Zoho."""

import re
# Two niches only, both backed by a real case study.
SEARCHES = {
    "real estate": [
        ("real estate team", "Phoenix, AZ"),
        ("real estate team", "Dallas, TX"),
        ("real estate team", "Austin, TX"),
        ("real estate team", "Tampa, FL"),
        ("real estate agency", "Brisbane, Australia"),
    ],
    "med spa": [
        ("med spa", "Scottsdale, AZ"),
        ("med spa", "Dallas, TX"),
        ("med spa", "Miami, FL"),
        ("cosmetic clinic", "Sydney, Australia"),
    ],
}

# How many listings to open per search, and how many leads to queue per run.
# Small on purpose: every lead gets reviewed by a person.
LISTINGS_PER_SEARCH = 12
MAX_QUEUED_PER_RUN = 15
MIN_SCORE_TO_QUEUE = 5

# Sending
MAX_SENDS_PER_DAY = 15
FOLLOWUP_1_AFTER_DAYS = 4
FOLLOWUP_2_AFTER_DAYS = 9

SHEET_NAME = "Maps Leads v2"
QUEUE_TAB = "Review Queue"
# Old v1 sheet: businesses already emailed there are never pitched again.
LEGACY_SHEETS = ["AI Automation Leads", "Maps Automation Leads"]

SENDER_NAME = "Damilola Akinbobola"
SENDER_EMAIL = "oluwa@automatesit.co"  # separate mailbox so outreach never risks the main inbox
SMTP_HOST = "smtp.zoho.com"
SMTP_PORT = 465

# Signature added by code, never by the model. US cold email (CAN-SPAM) needs a
# postal address; until POSTAL_ADDRESS is set, US leads are not drafted or sent.
SIGNATURE = """Damilola Akinbobola
Automates It | automatesit.co{postal_line}

If this isn't useful, just reply "no thanks" and I won't email again."""


def is_us(location: str) -> bool:
    """US cities are written "City, ST" in SEARCHES; "London, UK" is not US."""
    m = re.search(r",\s*([A-Z]{2})$", location.strip())
    return bool(m) and m.group(1) in US_STATES


US_STATES = set("""AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT
NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC""".split())
