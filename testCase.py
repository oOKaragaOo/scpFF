from datetime import date
from pathlib import Path
import time
import pandas as pd
from playwright.sync_api import sync_playwright

from core.airport_scraper import AirportScraper
from settings import SCRAPER_SETTINGS


# =========================================================
# CONFIG
# =========================================================

CSV_PATH = Path("data/reference/world_airports_city.csv")


# =========================================================
# TEST CASES
# =========================================================

TEST_CASES = [

    {
        "name": "export year mode (JHB)",
        "start": date(2026, 12, 10),
        "end": date(2027, 1, 10),
        "export_mode": "year",
        "rows": [
            {
                "country": "malaysia",
                "city": "Johor Bahru",
                "airport_name": "Sultan Ismail Intl",
                "airport_code": "JHB",
            }
        ],
    },

    {
        "name": "export month mode (JHB)",
        "start": date(2026, 2, 20),
        "end": date(2026, 3, 10),
        "export_mode": "month",
        "rows": [
            {
                "country": "malaysia",
                "city": "Johor Bahru",
                "airport_name": "Sultan Ismail Intl",
                "airport_code": "JHB",
            }
        ],
    },

    # =========================================
    # NEW — Weekly 2 airline (2 airport)
    # =========================================
    {
        "name": "weekly 2 airline (BKI + JHB)",
        "start": date(2026, 3, 1),
        "end": date(2026, 3, 20),
        "export_mode": "week",
        "rows": [
            {
                "country": "malaysia",
                "city": "Kota Kinabalu",
                "airport_name": "Kota Kinabalu Intl",
                "airport_code": "BKI",
            },
            {
                "country": "malaysia",
                "city": "Johor Bahru",
                "airport_name": "Sultan Ismail Intl",
                "airport_code": "JHB",
            }
        ],
    },

    # =========================================
    # NEW — Daily 3 airline
    # =========================================
    {
        "name": "daily 3 airline (BKI + JHB + KUL)",
        "start": date(2026, 3, 1),
        "end": date(2026, 3, 5),
        "export_mode": "day",
        "rows": [
            {
                "country": "malaysia",
                "city": "Kota Kinabalu",
                "airport_name": "Kota Kinabalu Intl",
                "airport_code": "BKI",
            },
            {
                "country": "malaysia",
                "city": "Johor Bahru",
                "airport_name": "Sultan Ismail Intl",
                "airport_code": "JHB",
            },
            {
                "country": "malaysia",
                "city": "Kuala Lumpur",
                "airport_name": "Kuala Lumpur Intl",
                "airport_code": "KUL",
            }
        ],
    }
]


# =========================================================
# HELPERS
# =========================================================

def write_airport_csv(rows):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(CSV_PATH, index=False)


def run_case(case):

    print("" + "=" * 70)
    print(f"🧪 TEST CASE: {case['name']}")
    print(f"📅 RANGE: {case['start']} -> {case['end']}")
    print("=" * 70)

    # ⭐ set export mode per case
    SCRAPER_SETTINGS["export_mode"] = case.get(
        "export_mode",
        "month"
    )

    print(f"📦 EXPORT MODE: {SCRAPER_SETTINGS['export_mode']}")

    # inject csv
    write_airport_csv(case["rows"])

    airports_df = pd.read_csv(CSV_PATH)
    codes = airports_df["airport_code"].dropna().unique().tolist()

    all_rows = []
    start_time = time.time()
    case_failed = False

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

                try:
                    Path("Debug/screenshots").mkdir(
                        parents=True,
                        exist_ok=True
                    )
                    shot_name = case["name"].replace(" ", "_")
                    page.screenshot(
                        path=f"Debug/screenshots/{shot_name}.png",
                        full_page=True
                    )
                    print("📸 Screenshot saved")
                except Exception as ss_err:
                    print("⚠️ screenshot fail:", ss_err)

                break

            time.sleep(2)

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
