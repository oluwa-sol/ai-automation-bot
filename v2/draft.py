"""Draft one pitch per lead with an LLM, then check it against the house rules.

The model only writes the middle of the email. Greeting, signature and the
opt-out line are added by code, so they can't drift.
"""

import json
import os
import re

from openai import OpenAI

from v2.enrich import _is_generic

# Only verified results. Never invent numbers beyond these.
PROOF = {
    "real estate": (
        "I built a lead system for a real estate team that pulls enquiries from Instagram, "
        "Facebook, WhatsApp and their website, qualifies each one and routes it to the right "
        "agent. First response went from 1 to 5 hours to under 90 seconds, and cold leads "
        "get followed up automatically every 30 days."
    ),
    "med spa": (
        "I built an intake system for a client that replies to every new enquiry with a "
        "personalised message within 60 seconds (it used to take 19 hours) and prepares the "
        "details before the consultation. It saves them 17.5 hours of admin a week."
    ),
}

RULES = """Write the middle of a short cold email (no greeting, no sign-off).
- 60 to 100 words, 3 short paragraphs.
- Paragraph 1 starts with the observed fact about THEIR business, written naturally the way a
  person would say it, naming the business once by its short everyday name (drop extras like
  "- EXP", "Real Estate Agent", city names or "| Scottsdale"). If the fact is a quoted phrase
  from their site, paraphrase it naturally rather than quoting it. Never open with "I came across", "I noticed",
  "I hope" or "I was looking". Never start with "Enquiries" or "Your enquiries".
- Paragraph 1, second sentence: what that usually means for a business like theirs, phrased as
  a common pattern ("usually", "often"), never as a claim about them.
- Paragraph 2: the proof, in first person, using ONLY the facts given. No other numbers.
- Paragraph 3: one short yes/no question that names the specific outcome for THEIR business,
  using the business's short name, e.g. "Would replying to every Ascend website enquiry within a
  minute be useful for your team right now?" Never "is this on your list", "this quarter", or a
  question built on the word "this". Never ask for a call, a meeting or "15 minutes".
- No links, no em dashes, no colons inside sentences, no exclamation marks, no AI model or
  tool names, no phrases like "stops being X and becomes Y", "game-changer", "leverage".
- Subject: 2 to 5 lowercase words naming THEIR business and what the email is about, e.g.
  "ascend's website enquiries". Never generic phrases like "contact form follow up". No question mark.
Return JSON only: {"subject": "...", "body": "..."}"""

BANNED = [r"—", r"–", r"\bI came across\b", r"\bI noticed\b", r"\bhope (this|you)\b",
          r"\b15 minutes\b", r"\bquick call\b", r"\bhop on\b", r"\bgame.?changer\b",
          r"\bleverage\b", r"\bstops? being\b", r"https?://", r"\bChatGPT\b", r"\bClaude\b",
          r"\bOpenAI\b", r"\bGPT\b", r"!", r"\bon your list\b", r"\bthis quarter\b",
          r"\bfollow up\b$"]


def check(subject: str, body: str) -> list[str]:
    """House-rule violations, empty if clean."""
    problems = [f"banned: {p}" for p in BANNED if re.search(p, subject + "\n" + body, re.I)]
    words = len(body.split())
    if not 55 <= words <= 110:
        problems.append(f"{words} words")
    if re.search(r"\w: \w", body):
        problems.append("colon inside a sentence")
    if subject != subject.lower() or "?" in subject:
        problems.append("subject format")
    return problems


def _prompt(lead: dict, niche: str, hook: str) -> str:
    facts = {
        "business": lead["name"], "city": lead["location"], "niche": niche,
        "observed_fact": hook, "google_reviews": lead.get("reviews"),
        "booking_tool_found": lead.get("booking_tools") or "none found",
        "chat_tool_found": lead.get("chat_tools") or "none found",
        "proof_you_may_use": PROOF[niche],
    }
    return RULES + "\n\nFacts (use only these):\n" + json.dumps(facts, indent=1)


def draft(lead: dict, niche: str, hook: str) -> dict:
    """Return {subject, body, problems}. problems is empty when the draft passes."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    out = {"subject": "", "body": "", "problems": ["not drafted"]}
    for _ in range(2):  # one retry if the first draft breaks a rule
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _prompt(lead, niche, hook)}],
            response_format={"type": "json_object"},
        )
        try:
            data = json.loads(resp.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            continue
        subject, body = _clean(data.get("subject", "")), _clean(data.get("body", ""))
        out = {"subject": subject, "body": body, "problems": check(subject, body)}
        if not out["problems"]:
            break
    return out


def _clean(text: str) -> str:
    """Repair accents that arrive as a NUL byte plus hex ("L\\x00e9 Nour" -> "Lé Nour")
    and drop any other control characters."""
    text = re.sub(r"\x00([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text).strip()


def greeting(lead: dict) -> str:
    """Greet whoever owns the inbox. A named contact on the site only counts if the
    email is a shared inbox; josh@ gets "Hi Josh," even if the site names Cheryl."""
    email = (lead.get("site_emails") or [""])[0]
    raw_local = email.split("@")[0].lower()
    local = re.split(r"[._\-+]", raw_local)[0]
    first = (lead.get("contact_name") or "").split(" ")[0]
    if len(first) < 3 or not first.isalpha():  # "As Co (Founder" scraped as a name
        first = ""
    if first and local == first.lower():
        return f"Hi {first},"
    if _looks_like_first_name(local, dotted="." in raw_local or "_" in raw_local) and not _is_generic(email):
        return f"Hi {local.capitalize()},"
    if first and _is_generic(email):
        return f"Hi {first},"
    return "Hi there,"


# Two-consonant starts that real first names use. "jholt" (initial + surname)
# or "drmarkwoo" don't start this way, so they get "Hi there," instead.
_NAME_ONSETS = ("bl", "br", "ch", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "kr",
                "ph", "pr", "sh", "st", "th", "tr", "wr")


def _looks_like_first_name(local: str, dotted: bool) -> bool:
    if not local.isalpha() or not 3 <= len(local) <= 8:
        return False
    if dotted:  # mark.buckley, james.prendergast: the first part is the name
        return True
    if local.startswith("dr") and len(local) > 5:  # drmarkwoo
        return False
    vowels = "aeiouy"
    if local[0] not in vowels and local[1] not in vowels and local[:2] not in _NAME_ONSETS:
        return False
    return len(local) <= 7
