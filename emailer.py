import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from scraper import get_pain_question

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
FROM_NAME = "Damilola"

ACCOUNT_1 = "oluwadameelola@gmail.com"   # 8am and 3pm runs
ACCOUNT_2 = "bamee221@gmail.com"          # 12pm run

SUBJECT_VARIANTS = [
    "quick question",
    "just a quick one",
    "had a question for you",
]

GENERIC_PREFIXES = {
    "info", "contact", "support", "help", "admin", "office", "hello",
    "enquiries", "enquiry", "inquiry", "sales", "team", "mail", "email",
    "reception", "general", "customerservice", "customer", "service",
    "bookings", "booking", "noreply", "no-reply", "accounts", "billing",
}


def extract_first_name(email: str) -> str:
    local = email.split("@")[0].lower()
    local = re.sub(r"[._\-+]", " ", local).strip()
    parts = local.split()
    if not parts:
        return ""
    first = parts[0]
    if first in GENERIC_PREFIXES or len(first) < 2:
        return ""
    if re.search(r"\d", first):
        return ""
    return first.capitalize()


def build_subject() -> str:
    from datetime import date
    day = date.today().toordinal()
    return SUBJECT_VARIANTS[day % len(SUBJECT_VARIANTS)]


def build_body(business_name: str, category: str, location: str, email: str = "") -> str:
    city = location.split(",")[0].strip()
    question = get_pain_question(category)
    first_name = extract_first_name(email) if email else ""
    greeting = f"Hi {first_name}," if first_name else "Hi,"

    return f"""{greeting}

I came across {business_name} while looking around {city} and had a quick question.

{question}

{FROM_NAME}"""


def build_followup_body(business_name: str, category: str, followup_day: int, email: str = "") -> str:
    first_name = extract_first_name(email) if email else ""
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    question = get_pain_question(category)

    if followup_day == 1:
        return f"""{greeting}

Sent you a message a few days ago but did not hear back, so wanted to try once more.

{question}

Only asking because I work with businesses like {business_name} on exactly this kind of thing and would love to know how you handle it currently.

{FROM_NAME}"""
    else:
        return f"""{greeting}

Last one from me.

I reached out twice with a question about how {business_name} handles things when the team is tied up. If now is not the right time, completely fine.

Feel free to reply whenever it becomes a priority.

{FROM_NAME}"""


# ---------------------------------------------------------------------------
# REPLY TEMPLATE — copy and send manually when someone replies
# ---------------------------------------------------------------------------
# Hi [their name],
#
# That makes sense, thanks for sharing that.
#
# The reason I asked is I help businesses like [Business Name] automate
# exactly that part. Things like follow-up messages, appointment reminders,
# after-hours enquiry handling — set up once and running in the background
# so your team is not doing it manually.
#
# Would it be okay if I walked you through what that could look like for
# [Business Name] specifically? Takes about 15 minutes and no commitment.
#
# Damilola
# ---------------------------------------------------------------------------


def send_email(to_email: str, business_name: str, category: str, location: str, password: str, from_email: str = ACCOUNT_1) -> bool:
    subject = build_subject()
    body = build_body(business_name, category, location, to_email)

    msg = MIMEMultipart()
    msg["From"] = f"{FROM_NAME} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        print(f"  [email] Sent to {to_email} via {from_email}")
        return True
    except Exception as e:
        print(f"  [email] Failed to send to {to_email}: {e}")
        return False


def send_followup(to_email: str, business_name: str, category: str, followup_day: int, password: str, from_email: str = ACCOUNT_1) -> bool:
    subject = "Re: quick question"
    body = build_followup_body(business_name, category, followup_day, to_email)

    msg = MIMEMultipart()
    msg["From"] = f"{FROM_NAME} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        print(f"  [follow up {followup_day}] Sent to {to_email} via {from_email}")
        return True
    except Exception as e:
        print(f"  [follow up {followup_day}] Failed to send to {to_email}: {e}")
        return False
