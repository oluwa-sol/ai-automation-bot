# Maps leads v2

Quality over volume: two niches (real estate teams, med spas), every email reviewed by a person, sent from oluwa@automatesit.co.

## Daily flow

1. **06:00 Lagos** `v2 Find and Draft Leads` adds up to 15 researched leads to the **Review Queue** tab of the "Maps Leads v2" sheet, each with a hook, a score, the reasoning and a draft. Nothing is sent.
2. **You review** each row:
   - Open the website and check the hook is true.
   - Edit Subject or Body if needed, then set Status to **APPROVED**, or **SKIP**.
   - Optional: form-test the best ones (send an enquiry, note how long they take to reply), write the result in **Notes**, set Status to **REDRAFT**. The next morning's run rewrites the email around it and sets it back to REVIEW.
3. **15:00 Lagos** `v2 Send Approved` sends APPROVED rows (max 15 a day) and follow-ups due on day 4 and day 9.
4. Mark anyone who answers as **REPLIED** so they get no follow-ups.

## Statuses

REVIEW, APPROVED, SKIP, REDRAFT, SENT, FU1 SENT, FU2 SENT, REPLIED

## GitHub secrets

GOOGLE_CREDENTIALS, OPENAI_API_KEY, ZOHO_APP_PASSWORD, POSTAL_ADDRESS

## Run locally

```bash
python -m v2.pipeline --niche "med spa" --limit 3
python -m v2.send --dry-run
```
