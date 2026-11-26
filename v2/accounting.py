"""Fixed email templates for the accounting niche (Document Chaser offer).

No AI writes these emails. The only per-firm facts are checked on the firm's own
website: its everyday name and that it does personal / individual tax returns.
UK, US and Australia each get their own deadline and documents.
Emails are drafted for review and sent by hand from dami@automatesit.co.
"""

import os
import re

from v2 import config
from v2.enrich import _is_generic
from v2.gap import short_name

DEMO_URL = "https://youtu.be/c3VCUS2RGwg"

# Evidence that the firm prepares personal tax returns (the first line of the email depends on it).
PERSONAL_TAX_RE = re.compile(
    r"self[\s-]?assessment|personal tax|individual tax|individual (income )?tax returns?|"
    r"personal (income )?tax returns?|form 1040|\b1040\b|individual returns?|"
    r"tax returns? for individuals|sole traders?|landlords?", re.I)

COMPANY_RE = re.compile(r"\b(ltd|limited|llp|plc)\b\.?", re.I)

TEMPLATES = {
    "UK": {
        "subject": "self assessment documents at {name}",
        "opener": ("{name} does self assessment returns, so January is usually when chasing "
                   "clients for P60s and bank statements takes up the most time."),
        "ask": "Would it help to have this running before the 31 January deadline?",
    },
    "US": {
        "subject": "tax season documents at {name}",
        "opener": ("{name} prepares individual tax returns, so tax season is usually when chasing "
                   "clients for W-2s, 1099s and receipts takes up the most time."),
        "ask": "Would it help to have this running before the April 15 rush?",
    },
    "AU": {
        "subject": "tax time documents at {name}",
        "opener": ("{name} prepares individual tax returns, so tax time is usually when chasing "
                   "clients for income statements, receipts and health insurance statements takes up the most time."),
        "ask": "Would it help to have this running before tax time opens in July?",
    },
}

MIDDLE = ("I built a small system that sends each client their own checklist, reminds them only "
          "about what's still missing, and shows you who's done in one tracker. You approve every "
          "message before it goes out.\n\n"
          "Here's a 1-minute demo of it working\n" + DEMO_URL)


def country(location: str) -> str:
    if config.is_us(location):
        return "US"
    if "australia" in location.lower():
        return "AU"
    return "UK"


def signature() -> str:
    address = os.environ.get("POSTAL_ADDRESS", "").strip()
    return config.SIGNATURE.format(postal_line=f"\n{address}" if address else "")


def pick_email(lead: dict, ctry: str) -> tuple[str, str]:
    """Return (email, reason_if_skipped). UK partnerships and sole traders are individuals
    under PECR, so for UK firms that aren't Ltd/LLP we only use a shared business inbox."""
    emails = lead.get("site_emails") or []
    if not emails:
        return "", "no email"
    if ctry != "UK" or COMPANY_RE.search(lead["name"]):
        return emails[0], ""
    generic = [e for e in emails if _is_generic(e)]
    if generic:
        return generic[0], ""
    return "", "UK firm not shown as Ltd/LLP and only a personal email found"


def build(lead: dict, location: str, greet: str) -> dict:
    """Return {subject, body, email, evidence, skip}. skip is a reason string when we must not draft."""
    ctry = country(location)
    if ctry == "US" and not os.environ.get("POSTAL_ADDRESS", "").strip():
        return {"skip": "US lead but POSTAL_ADDRESS is not set"}
    m = PERSONAL_TAX_RE.search(lead.get("site_text", ""))
    if not m:
        return {"skip": "no sign on their site that they do personal tax returns"}
    email, why = pick_email(lead, ctry)
    if not email:
        return {"skip": why}
    name = re.sub(r"[\s,]+(ltd|limited|llp|plc|inc|llc|pllc|pty|pty ltd|p\.?c\.?)\.?$", "", short_name(lead["name"]), flags=re.I).strip()
    t = TEMPLATES[ctry]
    body = "\n\n".join([greet, t["opener"].format(name=name), MIDDLE, t["ask"], signature()])
    return {"subject": t["subject"].format(name=name), "body": body, "email": email,
            "evidence": f"{ctry}: site mentions \"{m.group(0)}\"", "skip": ""}
