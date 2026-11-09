"""Rewrite drafts around a form test you ran yourself.

In the sheet, put what happened in Notes (e.g. "enquired Tue 10am, replied Thu 4pm")
and set Status to REDRAFT. This rewrites the body with that as the hook and puts
the row back to REVIEW, so you still approve it before anything sends.

Usage:  python -m v2.redraft
"""

from v2 import config
from v2.draft import draft
from v2.queue import open_queue, rows_with_status, update


def run():
    ws = open_queue(config.SHEET_NAME, config.QUEUE_TAB)
    rows = rows_with_status(ws, "REDRAFT")
    for r in rows:
        if not r["Notes"].strip():
            update(ws, r["_row"], Status="REVIEW", **{"Draft issues": "REDRAFT needs a form test result in Notes"})
            continue
        hook = f"when I sent an enquiry through their website: {r['Notes'].strip()}"
        lead = {"name": r["Business"], "location": r["City"], "reviews": r["Reviews"]}
        d = draft(lead, r["Niche"], hook)
        greet = r["Body"].split("\n", 1)[0] if r["Body"] else "Hi there,"
        update(ws, r["_row"], Status="REVIEW", Body=f"{greet}\n\n{d['body']}",
               Subject=d["subject"] or r["Subject"], **{
                   "Hook (verify on site)": f"form test: {r['Notes'].strip()}",
                   "Draft issues": "; ".join(d["problems"])})
        print(f"[redraft] {r['Business']}")
    print(f"[done] {len(rows)} rows redrafted.")


if __name__ == "__main__":
    run()
