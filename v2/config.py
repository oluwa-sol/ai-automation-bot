"""Settings for the v2 pipeline: two niches, a review queue, sending from Zoho."""

# Two niches only, both backed by a real case study.
SEARCHES = {
    "real estate": [
        ("real estate team", "Phoenix, AZ"),
        ("real estate team", "Dallas, TX"),
        ("real estate team", "Austin, TX"),
        ("real estate team", "Tampa, FL"),
        ("estate agents", "Manchester, UK"),
        ("real estate agency", "Brisbane, Australia"),
    ],
    "med spa": [
        ("med spa", "Scottsdale, AZ"),
        ("med spa", "Dallas, TX"),
        ("med spa", "Miami, FL"),
        ("aesthetics clinic", "London, UK"),
        ("aesthetics clinic", "Manchester, UK"),
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

# Signature added by code, never by the model. A postal address keeps US
# (CAN-SPAM) sends compliant; fill it in before sending to US leads.
SIGNATURE = """Damilola Akinbobola
Automates It | automatesit.co
{postal_address}

If this isn't useful, just reply "no thanks" and I won't email again."""
