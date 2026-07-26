import gspread
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Name", "Phone", "Email", "Reviews", "Lat", "Lng", "Category", "Location",
    "Date Added", "Follow Up 1", "Follow Up 2", "Status"
]


def get_or_create_sheet(sheet_name: str, credentials_file: str = "credentials.json"):
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open(sheet_name)
    sheet = spreadsheet.sheet1
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "Name":
        sheet.insert_row(HEADERS, 1)
    return sheet


def get_existing_names(sheet) -> set:
    all_values = sheet.col_values(1)
    return {name.strip().lower() for name in all_values[1:] if name.strip()}


def append_lead(sheet, lead: dict, existing: set) -> bool:
    name = lead.get("name", "").strip()
    if not lead.get("email", "").strip():
        print(f"  [skip] No email: {name}")
        return False
    if name.lower() in existing:
        print(f"  [skip] Already in sheet: {name}")
        return False

    today = date.today()
    row = [
        name,
        lead.get("phone", ""),
        lead.get("email", ""),
        lead.get("reviews", ""),
        lead.get("lat", ""),
        lead.get("lng", ""),
        lead.get("category", ""),
        lead.get("location", ""),
        str(today),
        str(today + timedelta(days=3)),
        str(today + timedelta(days=7)),
        "Pitched",
    ]
    sheet.append_row(row)
    existing.add(name.lower())
    return True


def get_followup_leads(sheet, followup_day: int) -> list[dict]:
    today = str(date.today())
    col = 10 if followup_day == 1 else 11   # Follow Up 1 = col J, Follow Up 2 = col K
    status_col = 12                          # Status = col L
    already_sent = f"Follow Up {followup_day} Sent"

    all_rows = sheet.get_all_values()
    due = []
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) < 12:
            continue
        followup_date = row[col - 1].strip()
        status = row[status_col - 1].strip()
        email = row[2].strip()

        if followup_date == today and email and status not in ("Replied", "Unsubscribed", already_sent):
            due.append({
                "row": i,
                "name": row[0],
                "email": email,
                "category": row[6],
                "location": row[7],
                "status": status,
            })
    return due


def mark_replied(sheet, row: int):
    sheet.update_cell(row, 12, "Replied")


def mark_followup_sent(sheet, row: int, followup_day: int):
    sheet.update_cell(row, 12, f"Follow Up {followup_day} Sent")
