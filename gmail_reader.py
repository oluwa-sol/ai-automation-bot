import imaplib

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
EMAIL = "oluwadameelola@gmail.com"


def get_imap_connection(password: str):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL, password)
    return mail


def has_replied(mail, lead_email: str) -> bool:
    try:
        mail.select("inbox")
        result, data = mail.search(None, f'(FROM "{lead_email}")')
        if result == "OK" and data[0]:
            return True
        return False
    except Exception as e:
        print(f"  [imap] Error checking reply from {lead_email}: {e}")
        return False
