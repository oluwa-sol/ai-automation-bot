"""Competitor gaps: something nearby competitors visibly do on their website that this lead doesn't.

Every gap is based on signals enrich() actually found on both websites, so the
email states a fact anyone can check by opening the two sites.
"""

# (key, check on an enriched lead, what the competitor does, what the lead does instead)
FEATURES = [
    ("chat",
     lambda l: bool(l.get("chat_tools")),
     "lets visitors start a chat or WhatsApp conversation straight from the website",
     "I could only find a contact form, no chat"),
    ("booking",
     lambda l: bool(l.get("booking_tools")),
     "lets people book a time online, any hour of the day",
     "I couldn't find a way to book online"),
]
# Only features we can SEE on both sites. "Instant follow-up" was dropped: we can't
# verify from outside how a business handles its inbox.


def short_name(name: str) -> str:
    """Everyday name: drop extras after separators like ' - ', ' | ', ' – '."""
    for sep in (" | ", " - ", " – ", " — ", ", "):
        name = name.split(sep)[0]
    return name.strip()


def find_gap(lead: dict, competitors: list[dict]) -> dict | None:
    """Return the strongest gap, or None if the lead already matches its competitors.

    Prefers the feature most competitors have, then the busiest competitor (most reviews).
    """
    others = [c for c in competitors
              if c.get("site_ok") and short_name(c["name"]).lower() != short_name(lead["name"]).lower()]
    best = None
    for key, has, they_do, lead_does in FEATURES:
        if has(lead) or lead.get("chat_tools") and key == "chat":
            continue
        with_it = [c for c in others if has(c)]
        if not with_it:
            continue
        top = max(with_it, key=lambda c: int(c.get("reviews") or 0))
        cand = {"feature": key, "competitor": short_name(top["name"]),
                "competitor_site": top.get("website", ""), "competitor_count": len(with_it),
                "they_do": they_do, "lead_does": lead_does}
        if best is None or cand["competitor_count"] > best["competitor_count"]:
            best = cand
    return best


def hook_text(gap: dict, lead_name: str) -> str:
    """One line for the review queue, so the reviewer can verify both sites."""
    return (f"gap: {gap['competitor']} {gap['they_do']} ({gap['competitor_site']}); "
            f"on {short_name(lead_name)}'s site: {gap['lead_does']}")
