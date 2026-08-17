import os
import re
from playwright.sync_api import sync_playwright

# Minimum review count to consider a business established enough
MIN_REVIEWS = 50

# Categories to target and the pain question to ask each
TARGET_CATEGORIES = {
    "dental":               "Do you handle appointment reminders manually or do you have something that takes care of that?",
    "dentist":              "Do you handle appointment reminders manually or do you have something that takes care of that?",
    "medical clinic":       "Do you handle appointment reminders and patient follow-ups manually or do you have something automated?",
    "salon":                "When a client cancels last minute, how do you usually fill that slot?",
    "nail salon":           "When a client cancels last minute, how do you usually fill that slot?",
    "hair salon":           "When a client cancels last minute, how do you usually fill that slot?",
    "barber":               "Do you handle your appointment bookings manually or do you have a system for that?",
    "spa":                  "How are you currently handling booking requests that come in outside of business hours?",
    "cleaning":             "How are you handling quote requests that come in after hours?",
    "law firm":             "How are you currently handling new client enquiries when your team is tied up?",
    "lawyer":               "How are you currently handling new client enquiries when your team is tied up?",
    "real estate":          "How are you currently following up with leads who enquire but do not book a viewing right away?",
    "estate agent":         "How are you currently following up with leads who enquire but do not book a viewing right away?",
    "gym":                  "How are you handling trial sign-ups and converting them to memberships right now?",
    "fitness":              "How are you handling trial sign-ups and converting them to memberships right now?",
    "tutor":                "How are you handling new student enquiries when you are already in a session?",
    "tutoring":             "How are you handling new student enquiries when you are already in a session?",
    "restaurant":           "How are you managing catering or event enquiries that come in outside opening hours?",
    "accountant":           "How are you currently handling new client onboarding once someone reaches out?",
    "accounting":           "How are you currently handling new client onboarding once someone reaches out?",
    "physiotherapy":        "Do you handle appointment reminders and follow-ups manually or do you have something automated?",
    "physio":               "Do you handle appointment reminders and follow-ups manually or do you have something automated?",
    "physical therapy":     "When a patient no-shows, does someone on your team follow up to rebook them or does that slot just go lost?",
    "occupational therapy": "When a patient no-shows, does someone on your team follow up to rebook them or does that slot just go lost?",
    "chiropractic":         "Do you handle appointment reminders and follow-ups manually or do you have something automated?",
    "chiropractor":         "Do you handle appointment reminders and follow-ups manually or do you have something automated?",
    "mortgage broker":      "How are you currently chasing clients for documents and keeping them updated through the process?",
    "mortgage":             "How are you currently chasing clients for documents and keeping them updated through the process?",
    "vet clinic":           "Do you send vaccination reminders and post-visit follow-ups manually or do you have something that handles that?",
    "veterinary":           "Do you send vaccination reminders and post-visit follow-ups manually or do you have something that handles that?",
    "immigration":          "How are you currently keeping clients updated on their case status and chasing documents?",
    "car dealership":       "How are you currently following up with people who come in for a test drive but do not buy on the day?",
    "dealership":           "How are you currently following up with people who come in for a test drive but do not buy on the day?",
    "property management":  "How are you currently handling maintenance requests and tenant communications day to day?",
    "driving school":       "How are you handling lesson bookings and test reminders for your students right now?",
    "insurance broker":     "How are you currently following up with leads who request a quote but go quiet?",
    "insurance":            "How are you currently following up with leads who request a quote but go quiet?",
}

DEFAULT_QUESTION = "How are you currently handling customer enquiries and follow-ups when your team is tied up?"


def get_pain_question(category: str) -> str:
    for key, question in TARGET_CATEGORIES.items():
        if key in category.lower():
            return question
    return DEFAULT_QUESTION


def build_query(category: str, location: str) -> str:
    from datetime import date
    variants = [
        f"{category} near {location}",
        f"{category} in {location}",
        f"best {category} {location}",
        f"{category} service {location}",
        f"local {category} {location}",
        f"{category} company {location}",
        f"top {category} {location}",
    ]
    day = date.today().toordinal()
    return variants[day % len(variants)]


def extract_review_count(page) -> int:
    try:
        for selector in [
            'button[jsaction*="pane.rating"]',
            'span[aria-label*="review"]',
            'div[role="img"][aria-label*="review"]',
        ]:
            el = page.locator(selector).first
            if el.count():
                text = el.get_attribute("aria-label") or el.inner_text(timeout=2000)
                m = re.search(r"([\d,]+)\s+review", text.lower().replace(",", ""))
                if m:
                    return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    return 0


def scrape_maps(category: str, location: str, max_results: int = 20) -> list[dict]:
    leads = []
    query = build_query(category, location)
    print(f"  [scraper] Query: {query}")

    with sync_playwright() as p:
        headless = os.environ.get("HEADLESS", "0") == "1"
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        print(f"  [scraper] Opening: {search_url}")
        page.goto(search_url)
        page.wait_for_timeout(2000)

        if "consent.google.com" in page.url:
            print("  [scraper] Consent page, accepting...")
            try:
                page.locator("button:has-text('Accept all')").click(timeout=5000)
            except Exception:
                try:
                    page.locator("form button").first.click(timeout=5000)
                except Exception:
                    pass
            page.wait_for_timeout(3000)
            if "consent.google.com" in page.url:
                page.goto(search_url)
                page.wait_for_timeout(3000)

        try:
            page.wait_for_selector('div[role="feed"]', timeout=15000)
        except Exception:
            print(f"  [scraper] No results feed. URL: {page.url}")
            browser.close()
            return []

        feed = page.locator('div[role="feed"]')
        prev, stale = 0, 0
        for _ in range(20):
            count = page.locator('div[role="feed"] > div').count()
            if count == prev:
                stale += 1
                if stale >= 3:
                    break
            else:
                stale = 0
            prev = count
            feed.evaluate("el => el.scrollTop += 3000")
            page.wait_for_timeout(1500)
            if page.locator("text=You've reached the end").count():
                break

        place_els = page.locator('a[href*="/maps/place/"]').all()
        place_urls = []
        for el in place_els:
            href = el.get_attribute("href")
            if href and href not in place_urls:
                place_urls.append(href)

        print(f"  [scraper] Found {len(place_urls)} listings, checking each...")

        for i, url in enumerate(place_urls[:max_results]):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)

                # Must have a real website — these are established businesses
                web_els = (
                    page.get_by_role("link", name="Website").all()
                    + page.locator("a[aria-label='Website']").all()
                )
                SOCIAL = ("instagram.com", "facebook.com", "fb.com", "tiktok.com",
                          "twitter.com", "x.com", "linkedin.com", "yelp.com")
                has_website = False
                website_url = ""
                for el in web_els:
                    href = (el.get_attribute("href") or "").lower()
                    if href and not any(s in href for s in SOCIAL):
                        has_website = True
                        website_url = href
                        break

                if not has_website:
                    print(f"  [skip {i+1}] no website")
                    continue

                # Must have enough reviews to show they are active
                review_count = extract_review_count(page)
                if review_count < MIN_REVIEWS:
                    print(f"  [skip {i+1}] only {review_count} reviews (min {MIN_REVIEWS})")
                    continue

                # Name
                name = ""
                try:
                    for el in page.locator("h1").all():
                        text = el.inner_text(timeout=1000).strip()
                        if text and not text.lower().startswith(("sponsored", "results", "google")):
                            name = text
                            break
                except Exception:
                    pass
                if not name:
                    print(f"  [skip {i+1}] no name")
                    continue

                # Phone
                phone = ""
                try:
                    el = page.locator('[data-tooltip="Copy phone number"]')
                    if el.count():
                        raw = el.first.get_attribute("aria-label") or ""
                        phone = raw.replace("Phone: ", "").strip()
                except Exception:
                    pass

                # Coordinates
                lat, lng = "", ""
                for src in [page.url, url]:
                    m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", src)
                    if m:
                        lat, lng = m.group(1), m.group(2)
                        break
                    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", src)
                    if m:
                        lat, lng = m.group(1), m.group(2)
                        break

                leads.append({
                    "name": name,
                    "phone": phone,
                    "lat": lat,
                    "lng": lng,
                    "reviews": review_count,
                    "website": website_url,
                    "category": category,
                    "location": location,
                })
                print(f"  [+] {name} | {phone} | {review_count} reviews")

            except Exception as e:
                print(f"  [!] Error on listing {i+1}: {e}")
                continue

        browser.close()

    return leads
