import re
import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

NOISE_DOMAINS = {
    "birdeye.com", "yext.com", "thryv.com", "podium.com", "yelp.com",
    "google.com", "facebook.com", "instagram.com", "tiktok.com",
    "example.com", "sentry.io", "wixpress.com", "squarespace.com",
    "mailchimp.com", "sendgrid.com", "hubspot.com", "zendesk.com",
    "freelance-banner.com", "yellowpages.com", "whitepages.com",
    "trulia.com", "zillow.com", "realtor.com", "hotfrog.com",
    "cylex.com", "brownbook.net", "bizify.co.uk", "freeindex.co.uk",
}

NOISE_KEYWORDS = {"privacy", "terms", "policy", "legal", "noreply", "no-reply", "unsubscribe"}

TEMPLATE_PATTERNS = re.compile(r"[\$#%]\{|__email__|your@email|\[email\]", re.IGNORECASE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


JUNK_PREFIXES = ("email", "mailto", "e-mail", "mail", "contact", "tel", "phone", "fax")


def clean_email(email: str) -> str:
    """Strip junk text that sometimes gets concatenated before the local part."""
    local, domain = email.split("@", 1)
    for prefix in JUNK_PREFIXES:
        if local.lower().startswith(prefix) and len(local) > len(prefix):
            candidate = local[len(prefix):]
            if candidate and candidate[0].isalpha():
                local = candidate
                break
    return f"{local}@{domain}"


def is_valid_email(email: str) -> bool:
    email = clean_email(email)
    domain = email.split("@")[-1].lower()
    local = email.split("@")[0].lower()
    if domain in NOISE_DOMAINS:
        return False
    if any(k in local for k in NOISE_KEYWORDS):
        return False
    if TEMPLATE_PATTERNS.search(email):
        return False
    return True


def extract_emails_from_text(text: str) -> list[str]:
    return [clean_email(e) for e in EMAIL_RE.findall(text) if is_valid_email(e)]


def scrape_page_for_email(url: str) -> str:
    try:
        r = requests.get(url, timeout=8, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        emails = extract_emails_from_text(soup.get_text(" "))
        if emails:
            return emails[0]
        # Also check mailto links
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("mailto:"):
                email = a["href"].replace("mailto:", "").split("?")[0].strip()
                if is_valid_email(email):
                    return email
    except Exception:
        pass
    return ""


def find_email_on_website(website_url: str) -> str:
    """Scrape the business website and its /contact page for an email."""
    base = website_url.rstrip("/")
    pages_to_try = [base, f"{base}/contact", f"{base}/contact-us", f"{base}/about"]
    for url in pages_to_try:
        try:
            email = scrape_page_for_email(url)
            if email:
                return email
        except Exception:
            continue
    return ""


def find_email(business_name: str, location: str, website_url: str = "") -> str:
    city = location.split(",")[0].strip()

    # Pass 0: Scrape the business website directly
    if website_url:
        email = find_email_on_website(website_url)
        if email:
            return email

    # Pass 1: DDG snippet search
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f'"{business_name}" {city} email contact', max_results=5))
        for r in results:
            emails = extract_emails_from_text(r.get("body", "") + r.get("title", ""))
            if emails:
                return emails[0]
    except Exception:
        pass

    # Pass 2: Visit top result pages
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{business_name} {city} contact", max_results=4))
        for r in results:
            url = r.get("href", "")
            if url and not any(n in url for n in NOISE_DOMAINS):
                email = scrape_page_for_email(url)
                if email:
                    return email
    except Exception:
        pass

    # Pass 3: Direct platform lookups
    try:
        with DDGS() as ddgs:
            for platform in ["site:facebook.com", "site:yelp.com"]:
                results = list(ddgs.text(f"{platform} {business_name} {city} email", max_results=2))
                for r in results:
                    emails = extract_emails_from_text(r.get("body", ""))
                    if emails:
                        return emails[0]
    except Exception:
        pass

    return ""
