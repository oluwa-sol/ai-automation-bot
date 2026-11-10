"""Send what you approved, and the follow-ups that are due, from Zoho.

Only rows you marked APPROVED are ever sent. Capped at MAX_SENDS_PER_DAY.
Needs env: ZOHO_APP_PASSWORD, POSTAL_ADDRESS.

Usage:
    python -m v2.send            # send for real
    python -m v2.send --dry-run  # print what would go out
    python -m v2.send --followups-only  # used by the 15:00 task
"""

import argparse
import os
import smtplib
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

from v2 import config
from v2.queue import open_queue, rows_with_status, update

FOLLOWUP_1 = """{greeting}

I know there's a lot competing for your attention right now, so I'll keep this short. If {topic} comes up later, or someone on your team looks after it, I'd be glad to help. Just reply here anytime."""

FOLLOWUP_2 = """{greeting}

This is my last note. If {topic} moves up your list later, you can reply to this anytime and I'll pick it up from there."""

TOPIC = {
    "real estate": "replying to new leads faster",
    "med spa": "getting back to new enquiries faster",
}


def _signature() -> str:
    address = os.environ.get("POSTAL_ADDRESS", "").strip()
    return config.SIGNATURE.format(postal_line=f"\n{address}" if address else "")


def _send(server, to: str, subject: str, body: str, dry: bool):
    msg = MIMEText(f"{body}\n\n{_signature()}", "plain", "utf-8")
    msg["From"] = formataddr((config.SENDER_NAME, config.SENDER_EMAIL))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="automatesit.co")
    if dry:
        print(f"\n--- would send to {to}: {subject}\n{msg.get_payload()}")
    else:
        server.sendmail(config.SENDER_EMAIL, [to], msg.as_string())


def _days_since(day: str) -> int:
    try:
        return (date.today() - date.fromisoformat(day.strip())).days
    except ValueError:
        return -1


def run(dry: bool, followups_only: bool = False):
    ws = open_queue(config.SHEET_NAME, config.QUEUE_TAB)
    today = str(date.today())
    budget = config.MAX_SENDS_PER_DAY

    # Follow-ups first: they're replies in an existing thread, cheapest to send.
    due = []
    for r in rows_with_status(ws, "SENT"):
        if _days_since(r["Sent"]) >= config.FOLLOWUP_1_AFTER_DAYS:
            due.append((r, "FU1 Sent", "FU1 SENT", FOLLOWUP_1))
    for r in rows_with_status(ws, "FU1 SENT"):
        if _days_since(r["Sent"]) >= config.FOLLOWUP_2_AFTER_DAYS:
            due.append((r, "FU2 Sent", "FU2 SENT", FOLLOWUP_2))
    # First emails only go out when the owner asks; the 15:00 task sends follow-ups only.
    approved = [] if followups_only else rows_with_status(ws, "APPROVED")
    if not due and not approved:
        print("[done] nothing approved or due.")
        return
    # Owner's decision (2026-11-09): send US rows without a postal address until the
    # CAC-registered address exists. CAN-SPAM expects one, so set POSTAL_ADDRESS as soon as possible.
    if not os.environ.get("POSTAL_ADDRESS", "").strip() and any(config.is_us(r["City"]) for r in approved):
        print("[warn] sending US emails without POSTAL_ADDRESS")

    server = None
    if not dry:
        server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30)
        server.login(config.SENDER_EMAIL, os.environ["ZOHO_APP_PASSWORD"])
    try:
        for r, date_col, status, template in due:
            if budget <= 0:
                break
            greet = r["Body"].split("\n", 1)[0]
            body = template.format(greeting=greet, topic=TOPIC.get(r["Niche"], "this"))
            _send(server, r["Email"], f"Re: {r['Subject']}", body, dry)
            if not dry:
                update(ws, r["_row"], Status=status, **{date_col: today})
            budget -= 1

        for r in approved:
            if budget <= 0:
                print("[cap] daily limit reached, the rest go tomorrow")
                break
            if not (r["Email"] and r["Subject"] and r["Body"]):
                print(f"[skip] row {r['_row']} is missing email, subject or body")
                continue
            _send(server, r["Email"], r["Subject"], r["Body"], dry)
            if not dry:
                update(ws, r["_row"], Status="SENT", Sent=today)
            budget -= 1
    finally:
        if server:
            server.quit()
    print(f"[done] {config.MAX_SENDS_PER_DAY - budget} emails {'previewed' if dry else 'sent'}.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--followups-only", action="store_true",
                   help="send due follow-ups but leave APPROVED first emails alone")
    a = p.parse_args()
    run(a.dry_run, a.followups_only)
