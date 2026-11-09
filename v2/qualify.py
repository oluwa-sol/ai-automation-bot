"""Score how likely a lead is to have the problem we solve, and pick the hook.

The hook is one observed fact from their site. The pitch is built around it,
so every email says something only that business would recognise.
"""


from v2.enrich import _is_generic


def score(lead: dict, niche: str) -> tuple[int, str, list[str]]:
    """Return (score, hook, reasons). Higher is a better fit."""
    reasons, s = [], 0
    if not lead.get("site_ok"):
        return 0, "", ["website did not load"]

    reviews = int(lead.get("reviews") or 0)
    if reviews >= 150:
        s += 2; reasons.append(f"{reviews} reviews (busy)")
    elif reviews >= 50:
        s += 1; reasons.append(f"{reviews} reviews")

    if lead.get("contact_name"):
        s += 2; reasons.append(f"named contact: {lead['contact_name']} ({lead['contact_title']})")
    emails = lead.get("site_emails", [])
    if emails and not _is_generic(emails[0]):
        s += 1; reasons.append("personal email")

    hook = ""
    if lead.get("slow_reply_text"):
        s += 3; hook = f'site says "{lead["slow_reply_text"]}"'
    elif niche == "med spa" and lead.get("call_to_book"):
        s += 3; hook = "booking is by phone call"
    elif not lead.get("chat_tools") and lead.get("has_form"):
        # Weak on its own (most sites have a form), so it only counts with other evidence.
        s += 1; hook = "enquiries go through a contact form with no instant reply"

    if niche == "med spa" and not lead.get("booking_tools"):
        s += 1; reasons.append("no online booking tool found")
    if niche == "real estate" and not lead.get("crm"):
        s += 1; reasons.append("no lead CRM found on site")

    # Already well covered: likely to say "we have that".
    covered = lead.get("chat_tools", []) + lead.get("crm", [])
    if covered:
        s -= 2; reasons.append("already uses " + ", ".join(covered))

    return s, hook, reasons
