# """
# TastScript.py

# Mini test runner for flight scraper scenarios.

# Purpose
# -------
# - Inject START_DATE / END_DATE for each test case
# - Rewrite world_airports_city.csv per case
# - Run main-like flow with AirportScraper
# - Useful for regression testing calendar + reload behavior

# How to run
# ----------
# python TastScript.py

# Notes
# -----
# - This is an integration-style test (not pure unit test)
# - It uses real Playwright browser + real website
# - Designed for quick reproducible scenario testing
# """

from datetime import date
from pathlib import Path
import time
import pandas as pd
from playwright.sync_api import sync_playwright

from core.airport_scraper import AirportScraper


# =========================================================
# CONFIG
# =========================================================

CSV_PATH = Path("data/reference/world_airports_city.csv")


# =========================================================
# TEST CASES
# =========================================================

TEST_CASES = [
    {
        "name": "ย้อนหลัง + ข้ามหลายวัน (DSY)",
        "start": date(2026, 2, 27),
        "end": date(2026, 3, 2),
        "rows": [
            {
                "country": "cambodia",
                "city": "Krong Khemara Phoumin",
                "airport_name": "Dara Sakor Intl",
                "airport_code": "DSY",
            }
        ],
    },
    {
        "name": "target อยู่ grid เดือนก่อนหน้า (UTH)",
        "start": date(2026, 3, 1),
        "end": date(2026, 3, 2),
        "rows": [
            {
                "country": "Thailand",
                "city": "Udon Thani",
                "airport_name": "Udon Thani",
                "airport_code": "UTH",
            }
        ],
    },
    {
        "name": "boundary month repeat (DSY)",
        "start": date(2026, 2, 2),
        "end": date(2026, 3, 2),
        "rows": [
            {
                "country": "cambodia",
                "city": "Krong Khemara Phoumin",
                "airport_name": "Dara Sakor Intl",
                "airport_code": "DSY",
            }
        ],
    },
    {
        "name": "mini long run (+/-100 rows behavior) (BKI)",
        "start": date(2026, 2, 25),
        "end": date(2026, 3, 2),
        "rows": [
            {
                "country": "malaysia",
                "city": "Kota Kinabalu",
                "airport_name": "Kota Kinabalu",
                "airport_code": "BKI",
            }
        ],
    },
]


# =========================================================
# HELPERS
# =========================================================

def write_airport_csv(rows):
    # """Overwrite world_airports_city.csv for each test case."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(CSV_PATH, index=False)


def run_case(case):
    # """Run one scenario using the same logic as main.py."""

    print("" + "=" * 70)
    print(f"🧪 TEST CASE: {case['name']}")
    print(f"📅 RANGE: {case['start']} -> {case['end']}")
    print("=" * 70)

    # inject csv
    write_airport_csv(case["rows"])

    airports_df = pd.read_csv(CSV_PATH)
    codes = airports_df["airport_code"].dropna().unique().tolist()

    all_rows = []
    start_time = time.time()
    case_failed = False

    # ⭐ browser restart every case (isolated session)
    with sync_playwright() as p:

        ctx = p.chromium.launch_persistent_context(
            "profile_test",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = ctx.new_page()
        scraper = AirportScraper(page)

        for i, code in enumerate(codes, 1):
            print(f"[{i}/{len(codes)}] {code}")

            try:
                rows = scraper.scrape_airport(
                    code,
                    case["start"],
                    case["end"],
                )
                all_rows.extend(rows)

            except Exception as e:
                case_failed = True
                print("❌ ERROR:", e)

                # ⭐ auto screenshot on failure
                try:
                    Path("Debug/screenshots").mkdir(parents=True, exist_ok=True)
                    shot_name = case["name"].replace(" ", "_")
                    page.screenshot(
                        path=f"Debug/screenshots/{shot_name}.png",
                        full_page=True
                    )
                    print("📸 Screenshot saved")
                except Exception as ss_err:
                    print("⚠️ screenshot fail:", ss_err)

                # break current case immediately
                break

            time.sleep(2)

        # ⭐ ensure browser closed before next case
        ctx.close()

    elapsed = time.time() - start_time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    if case_failed:
        print(f"⚠️ CASE FAILED | ROWS: {len(all_rows)}")
    else:
        print(f"✅ CASE DONE | ROWS: {len(all_rows)}")

    print(f"⏱ Runtime: {mins}m {secs}s")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("🔥 Start TastScript integration tests")

    for case in TEST_CASES:
        run_case(case)

    print("\n🏁 ALL TESTS FINISHED")
