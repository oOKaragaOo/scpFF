from datetime import date
from playwright.sync_api import sync_playwright
from core.airport_scraper import AirportScraper
import pandas as pd
import time
program_start = time.time()
START_DATE = date(2026, 2, 1)
END_DATE   = date(2026, 2, 28)

airports_df = pd.read_csv("data/reference/world_airports_city.csv")
codes = airports_df["airport_code"].dropna().unique().tolist()

all_rows = []

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        "profile",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )

    page = ctx.new_page()

    scraper = AirportScraper(page)

    for i, code in enumerate(codes, 1):
        print(f"[{i}/{len(codes)}] {code}")

        try:
            rows = scraper.scrape_airport(
                code, START_DATE, END_DATE
            )
            all_rows.extend(rows)

        except Exception as e:
            print(" ERROR:", e)

        time.sleep(2)

    ctx.close()

program_end = time.time()
elapsed = program_end - program_start

mins = int(elapsed // 60)
secs = int(elapsed % 60)
print(f"\n⏱ Runtime: {mins}m {secs}s")