import json
from sheets import get_or_create_sheet, get_followup_leads, mark_replied, mark_followup_sent
from emailer import send_followup
from gmail_reader import get_imap_connection, has_replied

with open("saved_config.json") as f:
    PASSWORD = json.load(f)["gmail_password"]

SHEET = "AI Automation Leads"
CREDENTIALS = "credentials.json"


def process_followups(followup_day: int, sheet):
    leads = get_followup_leads(sheet, followup_day)
    print(f"\n[*] Follow up {followup_day}: {len(leads)} leads due today")

    for lead in leads:
        email = lead["email"]
        name = lead["name"]
        category = lead["category"]

        try:
            mail = get_imap_connection(PASSWORD)
            replied = has_replied(mail, email)
            try:
                mail.logout()
            except Exception:
                pass
        except Exception as e:
            print(f"  [imap] Could not check reply for {email}: {e}")
            replied = False

        if replied:
            print(f"  [replied] {name} — marking as Replied")
            mark_replied(sheet, lead["row"])
            continue

        success = send_followup(email, name, category, followup_day, PASSWORD)
        if success:
            mark_followup_sent(sheet, lead["row"], followup_day)


if __name__ == "__main__":
    print("[*] Starting follow up checks...")
    sheet = get_or_create_sheet(SHEET, CREDENTIALS)

    process_followups(1, sheet)
    process_followups(2, sheet)

    print("\n[done] Follow up run complete.")
