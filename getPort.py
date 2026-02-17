from playwright.sync_api import sync_playwright
import csv
import re
import time
import random

def parse_airport(text):
    m = re.search(r"(.+?)\s*\(([A-Z]{3})\)", text)
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2)

def load_all_cities(page, max_round=40):
    last = 0
    for _ in range(max_round):
        page.evaluate("""
            () => {
              const el = document.querySelector('#sbar-fromdd');
              if (el) el.scrollTop = el.scrollHeight;
            }
        """)
        time.sleep(random.uniform(0.4, 0.7))

        count = page.evaluate("""
            () => document.querySelectorAll(
              '#sbar-fromdd details.sbar-nest details.sbar-nest'
            ).length
        """)

        if count == last:
            return
        last = count
#------ Input search
countries = [
    "Dallas"
]

rows = set()

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = browser.new_page()

    page.goto("https://www.flightsfrom.com/", timeout=60000)
    page.wait_for_selector("#sbar-frominput")

    for country in countries:
        print("SCRAP:", country)

        page.click("#sbar-frominput")
        page.fill("#sbar-frominput", "")
        page.type("#sbar-frominput", country, delay=random.randint(90, 140))

        page.wait_for_selector("#sbar-fromdd details.sbar-nest", timeout=30000)

        page.evaluate("""
            () => {
              document
                .querySelectorAll('#sbar-fromdd > details.sbar-nest')
                .forEach(d => d.open = true);
            }
        """)

        load_all_cities(page)

        city_details = page.query_selector_all(
            "#sbar-fromdd details.sbar-nest details.sbar-nest"
        )

        for detail in city_details:
            detail.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.6))

            detail.evaluate("el => el.open = true")
            time.sleep(random.uniform(0.3, 0.6))

            summary = detail.query_selector("summary")
            if not summary:
                continue

            city_el = summary.query_selector("div.sbar-entry-primary")
            if not city_el:
                continue

            city = city_el.inner_text().strip()

            airport_spans = detail.query_selector_all(
                "li span.sbar-entry-primary-main"
            )

            for span in airport_spans:
                text = span.inner_text().strip()
                airport_name, airport_code = parse_airport(text)
                if not airport_code:
                    continue

                rows.add((
                    country,
                    city,
                    airport_name,
                    airport_code
                ))

        time.sleep(random.uniform(0.8, 1.2))

    browser.close()

with open("data/reference/world_airports_city.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "country",
        "city",
        "airport_name",
        "airport_code"
    ])
    for r in sorted(rows):
        writer.writerow(r)

print("TOTAL ROWS:", len(rows))
