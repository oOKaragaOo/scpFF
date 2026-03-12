from playwright.sync_api import sync_playwright
import csv
import time
import random
from urllib.parse import quote
import argparse

def parse_countries(tokens):
    parts = []
    current = []
    for token in tokens:
        pieces = token.split(",")
        for i, piece in enumerate(pieces):
            if i == 0:
                if piece:
                    current.append(piece)
            else:
                name = " ".join(current).strip()
                if name:
                    parts.append(name)
                current = []
                if piece:
                    current.append(piece)
    name = " ".join(current).strip()
    if name:
        parts.append(name)
    return parts

def slugify_country(name):
    return "-".join(name.strip().split())
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--country",
        required=True,
        nargs="+",
        help="Comma-separated country list, e.g. thailand, usa"
    )
    args = parser.parse_args()

    countries = parse_countries(args.country)
    if not countries:
        raise SystemExit("No countries provided.")

    rows = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.new_page()

        for country in countries:
            print("SCRAP:", country)

            country_slug = quote(slugify_country(country))
            page.goto(f"https://www.flightsfrom.com/{country_slug}", timeout=60000)
            page.wait_for_selector(".box-airport-item", timeout=30000)

            items = page.query_selector_all(".box-airport-item")

            for item in items:
                item.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.2, 0.4))

                first_div = item.query_selector("a.box-airport-link > div")
                if not first_div:
                    continue

                spans = first_div.query_selector_all("span")
                if len(spans) < 2:
                    continue

                city = spans[0].inner_text().strip()
                airport_code = spans[1].inner_text().strip()
                if not airport_code:
                    continue

                airport_name = city

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

if __name__ == "__main__":
    main()
