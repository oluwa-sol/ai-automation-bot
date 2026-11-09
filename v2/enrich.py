"""Read a lead's website and record what it shows, so the pitch is based on evidence.

Every signal here is something a person can confirm by opening the site.
"""

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from email_finder import HEADERS, extract_emails_from_text, is_valid_email

# Tools that already solve the problem we'd pitch. Finding one is a reason to
# skip or soften the pitch, not to claim they have nothing.
BOOKING_TOOLS = {
    "vagaro": "Vagaro", "joinblvd": "Boulevard", "boulevard": "Boulevard",
    "mindbodyonline": "Mindbody", "fresha": "Fresha", "zenoti": "Zenoti",
    "aestheticspro": "AestheticsPro", "acuityscheduling": "Acuity",
    "janeapp": "Jane", "squareup.com/appointments": "Square Appointments",
    "calendly": "Calendly", "glossgenius": "GlossGenius", "pabau": "Pabau",
    "phorest": "Phorest",
}
CHAT_TOOLS = {
    "podium": "Podium", "birdeye": "Birdeye", "intercom": "Intercom",
    "tidio": "Tidio", "livechatinc": "LiveChat", "drift.com": "Drift",
    "tawk.to": "Tawk", "hubspot.com/conversations": "HubSpot chat",
    "leadconnectorhq": "GoHighLevel", "msgsndr": "GoHighLevel",
    "wa.me": "WhatsApp link", "manychat": "ManyChat",
}
REAL_ESTATE_CRMS = {
    "followupboss": "Follow Up Boss", "kvcore": "kvCORE", "lofty": "Lofty",
    "chime.me": "Lofty", "boomtownroi": "BoomTown", "sierrainteractive": "Sierra",
    "realgeeks": "Real Geeks", "ylopo": "Ylopo", "cincpro": "CINC",
    "brivity": "Brivity", "propertybase": "Propertybase",
}

SLOW_REPLY_RE = re.compile(
    r"(within|in)\s+(24|48|72)\s*(hours|hrs)|(one|1|two|2)\s+business\s+days?|"
    r"we('ll| will) (get back|be in touch|respond)", re.I)
CALL_TO_BOOK_RE = re.compile(r"call (us )?to (book|schedule)|book by (phone|calling)", re.I)
NAME_TITLE_RE = re.compile(
    r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})\s*[,\-|]?\s*"
    r"(Founder|Owner|Co-Founder|Medical Director|Broker|Team Lead(?:er)?|Principal|"
    r"Managing Director|Director|Lead Injector|CEO)", re.M)


def _get(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, timeout=10, headers=HEADERS)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            return None
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException:
        return None


def _candidate_pages(home: BeautifulSoup, base: str) -> list[str]:
    """Contact, about and team pages linked from the homepage, same domain only."""
    host = urlparse(base).netloc
    pages = []
    for a in home.find_all("a", href=True):
        text = (a.get_text(" ") + " " + a["href"]).lower()
        if any(w in text for w in ("contact", "about", "team", "our-agents", "meet")):
            url = urljoin(base, a["href"]).split("#")[0]
            if urlparse(url).netloc == host and url not in pages:
                pages.append(url)
    return pages[:4]


def _find(mapping: dict, html: str) -> list[str]:
    return sorted({label for key, label in mapping.items() if key in html})


def enrich(lead: dict) -> dict:
    """Return the lead with website evidence added. Never raises."""
    base = lead.get("website", "")
    out = {**lead, "booking_tools": [], "chat_tools": [], "crm": [], "slow_reply_text": "",
           "call_to_book": False, "contact_name": "", "contact_title": "",
           "site_emails": [], "has_form": False, "site_ok": False}
    home = _get(base) if base else None
    if home is None:
        return out
    out["site_ok"] = True

    soups = [home] + [s for s in (_get(u) for u in _candidate_pages(home, base)) if s]
    html = " ".join(str(s).lower() for s in soups)
    text = " ".join(s.get_text(" ") for s in soups)

    out["booking_tools"] = _find(BOOKING_TOOLS, html)
    out["chat_tools"] = _find(CHAT_TOOLS, html)
    out["crm"] = _find(REAL_ESTATE_CRMS, html)
    out["has_form"] = any(s.find("form") for s in soups)
    out["call_to_book"] = bool(CALL_TO_BOOK_RE.search(text))
    m = SLOW_REPLY_RE.search(text)
    out["slow_reply_text"] = m.group(0) if m else ""

    for m in NAME_TITLE_RE.finditer(text):
        if _looks_like_person(m.group(1)):
            out["contact_name"], out["contact_title"] = m.group(1), m.group(2)
            break

    emails = extract_emails_from_text(text)
    for s in soups:
        for a in s.find_all("a", href=True):
            if a["href"].startswith("mailto:"):
                e = a["href"][7:].split("?")[0].strip()
                if is_valid_email(e):
                    emails.append(e)
    site_domain = urlparse(base).netloc.replace("www.", "")
    # Prefer addresses on the business's own domain, then personal-looking ones.
    emails = sorted(set(emails), key=lambda e: (site_domain not in e, _is_generic(e)))
    out["site_emails"] = emails[:3]
    return out


# Words that start "Our Medical Director", "Meet The Team" and similar phrases,
# which the name pattern would otherwise read as a person.
NOT_NAMES = {
    "our", "the", "meet", "your", "certified", "licensed", "board", "medical", "lead",
    "about", "with", "and", "by", "from", "contact", "call", "book", "real", "estate",
    "team", "senior", "associate", "managing", "nurse", "registered", "aesthetic",
    "dr", "doctor", "founded", "owned", "local", "award", "top", "best", "new",
}


def _looks_like_person(name: str) -> bool:
    words = name.split()
    return 2 <= len(words) <= 3 and not any(w.lower().strip(".") in NOT_NAMES for w in words)


def _is_generic(email: str) -> bool:
    return email.split("@")[0].lower() in {
        "info", "contact", "hello", "office", "admin", "enquiries", "inquiries",
        "bookings", "booking", "reception", "team", "sales", "support", "frontdesk",
        "concierge", "appointments", "care", "spa", "clinic", "marketing"}
