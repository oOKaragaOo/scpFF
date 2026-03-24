from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import csv
import time
import random
import argparse
from pathlib import Path
from urllib.parse import quote
import re
from tqdm import tqdm


def slugify_country(name):
    normalized = name.strip().lower()
    normalized = normalized.replace(",", "")
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")


def normalize_slug(name, href):
    slug = (href or "").strip().lstrip("/").strip().lower()
    if not slug:
        return slugify_country(name)

    slug = slug.replace("%2c", "").replace(",", "")
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def normalize_continent_slug(continent):
    return slugify_country(continent)


def should_include_continent(continent, selected_continent):
    if selected_continent == "all":
        return True
    return normalize_continent_slug(continent) == selected_continent


def scrape_countries(page):
    countries = []
    seen = set()

    page.goto("https://www.flightsfrom.com/countries", timeout=60000)
    page.wait_for_selector(".row", timeout=30000)

    rows = page.query_selector_all(".row")

    for row in rows:
        continent_el = row.query_selector(".col-xs-12")
        if not continent_el:
            continue

        continent = continent_el.inner_text().strip()
        if not continent:
            continue

        links = row.query_selector_all('.col-xs-6.col-sm-3 a[href^="/"]')

        for link in links:
            href = (link.get_attribute("href") or "").strip()
            name = link.inner_text().strip()

            if not href.startswith("/") or not name:
                continue

            slug = normalize_slug(name, href)
            if not slug or slug in seen:
                continue

            seen.add(slug)
            countries.append((continent, name, slug))

    return countries


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "continent",
            "country",
            "city",
            "airport_name",
            "airport_code"
        ])
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--continent",
        default="all",
        help="Choose a continent slug like 'north-america' or use 'all'."
    )
    parser.add_argument(
        "--output",
        default="data/reference/country_airport_stats.csv",
        help="CSV output path."
    )
    args = parser.parse_args()
    selected_continent = normalize_continent_slug(args.continent)

    rows = set()
    total_airports = 0
    errors = []
    started_at = time.perf_counter()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = browser.new_page()
        countries = scrape_countries(page)

        if not countries:
            browser.close()
            raise SystemExit("No countries found on flightsfrom.com/countries.")

        countries = [
            country for country in countries
            if should_include_continent(country[0], selected_continent)
        ]

        if not countries:
            browser.close()
            raise SystemExit(f"No countries found for continent: {args.continent}")

        for continent, country_name, country_slug in tqdm(countries, desc="Scraping countries", unit="country"):
            try:
                safe_slug = quote(country_slug)
                page.goto(f"https://www.flightsfrom.com/{safe_slug}", timeout=60000)
                page.wait_for_selector(".box-airport-item", timeout=30000)
                items = page.query_selector_all(".box-airport-item")
            except PlaywrightTimeoutError:
                error_message = f"TIMEOUT: {country_name} ({country_slug})"
                print(error_message)
                errors.append(error_message)
                continue

            for item in items:
                item.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.15, 0.3))

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
                    continent,
                    country_name,
                    city,
                    airport_name,
                    airport_code
                ))

            total_airports = len(rows)
            time.sleep(random.uniform(0.8, 1.2))

        browser.close()

    output_path = Path(args.output)
    sorted_rows = sorted(rows, key=lambda row: (row[0], row[1], row[2], row[4]))
    write_csv(output_path, sorted_rows)

    continent_groups = {}
    for row in sorted_rows:
        continent_groups.setdefault(row[0], []).append(row)

    for continent, continent_rows in continent_groups.items():
        continent_slug = normalize_continent_slug(continent)
        continent_output = output_path.with_name(
            f"{output_path.stem}_{continent_slug}{output_path.suffix}"
        )
        write_csv(continent_output, continent_rows)

    total_countries = len({(row[0], row[1]) for row in sorted_rows})
    elapsed_seconds = time.perf_counter() - started_at
    elapsed_minutes = round(elapsed_seconds / 60, 2)
    print("TOTAL COUNTRIES:", total_countries)
    print("TOTAL AIRPORTS:", total_airports)
    print("TOTAL ERRORS:", len(errors))
    print("TIME USED (MIN):", elapsed_minutes)
    print("OUTPUT:", output_path)


if __name__ == "__main__":
    main()
