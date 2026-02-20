from datetime import date
from playwright.sync_api import sync_playwright
from core.airport_scraper import AirportScraper
from core.SoundNotifier import SoundNotifier
import pandas as pd
import time

# 🔥 IMPORT SETTINGS (ปรับ path ให้ตรงของคุณ)
from settings import SCRAPER_SETTINGS


program_start = time.time()

START_DATE = date(2026, 2, 24)
END_DATE   = date(2026, 2, 26)

airports_df = pd.read_csv("data/reference/world_airports_city.csv")
codes = airports_df["airport_code"].dropna().unique().tolist()

all_rows = []

# =========================
# INIT NOTIFIER
# =========================
notifier = SoundNotifier()

# =========================
# RESTART SETTINGS
# =========================
RESTART_ENABLED = SCRAPER_SETTINGS.get("restart_enabled", False)
RESTART_EVERY = SCRAPER_SETTINGS.get("restart_every_days", 180)

global_day_counter = 0


# =========================
# MAIN PROCESS
# =========================
try:

    with sync_playwright() as p:

        for i, code in enumerate(codes, 1):

            print(f"\n[{i}/{len(codes)}] {code}")

            # =========================
            # OPEN BROWSER PER AIRPORT
            # =========================
            ctx = p.chromium.launch_persistent_context(
                "profile",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )

            page = ctx.new_page()
            scraper = AirportScraper(page)

            try:
                rows = scraper.scrape_airport(
                    code,
                    START_DATE,
                    END_DATE
                )

                all_rows.extend(rows)

            except Exception as e:
                print(" ERROR:", e)

            finally:
                print(f"🔄 Closing browser for airport: {code}")
                ctx.close()

            time.sleep(2)

    notifier.success()

except Exception as e:
    print("❌ Fatal Crash:", e)
    notifier.error()
    raise
    print("❌ Fatal Crash:", e)
    notifier.error()
    raise


# =========================
# RUNTIME
# =========================
program_end = time.time()
elapsed = program_end - program_start

mins = int(elapsed // 60)
secs = int(elapsed % 60)

print(f"\n⏱ Runtime: {mins}m {secs}s")