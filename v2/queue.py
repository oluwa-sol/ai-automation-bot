"""The review queue: one Google Sheet tab where every lead waits for a person.

Status flow: REVIEW -> APPROVED (you) -> SENT -> FU1 SENT -> FU2 SENT
             REVIEW -> SKIP (you)          any -> REPLIED (you)
Edit the Subject or Body cells freely before approving; the sender uses
whatever is in the sheet.
"""

import time

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

COLUMNS = ["Status", "Score", "Niche", "Business", "City", "Website", "Reviews",
           "Contact", "Email", "Hook (verify on site)", "Why it scored", "Subject", "Body",
           "Draft issues", "Date Added", "Sent", "FU1 Sent", "FU2 Sent", "Notes"]
COL = {name: i + 1 for i, name in enumerate(COLUMNS)}


def _retry(fn, *a, **kw):
    for attempt in range(5):
        try:
            return fn(*a, **kw)
        except gspread.exceptions.APIError:
            if attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))


def open_queue(sheet_name: str, tab: str, credentials_file: str = "credentials.json"):
    client = gspread.authorize(Credentials.from_service_account_file(credentials_file, scopes=SCOPES))
    # The sheet lives in the owner's Drive and is shared with the service account,
    # which has no Drive storage of its own and can't create files.
    book = _retry(client.open, sheet_name)
    try:
        ws = book.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(tab, rows=1000, cols=len(COLUMNS))
    if _retry(ws.row_values, 1) != COLUMNS:
        _retry(ws.update, values=[COLUMNS], range_name="A1")
    return ws


def known_businesses(ws, legacy_sheets: list[str], credentials_file: str = "credentials.json") -> set:
    """Lower-cased names already in the queue or emailed by the old v1 bot."""
    names = {n.strip().lower() for n in _retry(ws.col_values, COL["Business"])[1:] if n.strip()}
    client = gspread.authorize(Credentials.from_service_account_file(credentials_file, scopes=SCOPES))
    for title in legacy_sheets:
        try:
            old = _retry(client.open, title).sheet1
            names |= {n.strip().lower() for n in _retry(old.col_values, 1)[1:] if n.strip()}
        except gspread.SpreadsheetNotFound:
            pass
    return names


def append_rows(ws, rows: list[dict]):
    if rows:
        _retry(ws.append_rows, [[r.get(c, "") for c in COLUMNS] for r in rows],
               value_input_option="RAW")


def rows_with_status(ws, *statuses: str) -> list[dict]:
    values = _retry(ws.get_all_values)
    out = []
    for i, row in enumerate(values[1:], start=2):
        row = row + [""] * (len(COLUMNS) - len(row))
        rec = dict(zip(COLUMNS, row))
        if rec["Status"].strip().upper() in statuses:
            rec["_row"] = i
            out.append(rec)
    return out


def update(ws, row: int, **fields):
    for name, value in fields.items():
        _retry(ws.update_cell, row, COL[name], value)
