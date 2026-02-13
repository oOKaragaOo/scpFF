from datetime import timedelta
from services.calendar_service import CalendarService
from services.loader_service import LoaderService
from services.parser_service import ParserService
from utils.exporter import export_day_debug


class AirportScraper:

    def __init__(self, page):
        self.page = page
        self.calendar = CalendarService(page)
        self.loader = LoaderService(page)
        self.parser = ParserService(page, self.loader)
# =========================
# PRIVATE HELPERS
# =========================

    def snapshot_flights(self):

        self.loader.wait_list_stable()

        locator = self.page.locator("li.ff-li-list.deparr")
        dom_count = locator.count()

        flights = set()

        for i in range(dom_count):
            flight_code = locator.nth(i).locator(
                ".deparr_flight"
            ).inner_text()

            flights.add(flight_code.strip())

        print(f"   📸 Snapshot DOM count: {dom_count}")
        print(f"   🧾 Snapshot unique flights: {len(flights)}")

        return flights

    def reset_if_large_dataset(self, row_count, threshold=100):

        if row_count > threshold:
            print("   🔄 Large dataset detected, reloading page...")
            self.page.reload()
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(800)
            return True

        return False

    def _open_airport_page(self, code):

        self.page.goto(
            f"https://www.flightsfrom.com/{code}"
            f"?from={code}&entityType=arrivals&take=100"
            "&dateMethod=month&sorting=arrival-time"
            "&sortingDirection=asc&state=1",
            timeout=60000
        )

    def scrape_current_month(self, code, current_month, start_date, end_date):

        from datetime import date
        import time

        year = current_month.year
        month = current_month.month

        month_rows = []

        print(f"\n🗓 Processing month: {current_month.strftime('%Y-%m')}")

        self._prepare_month(year, month)

        for day in range(1, 32):

            try:
                page_date = date(year, month, day)
            except:
                break

            if page_date < start_date or page_date > end_date:
                continue

            print(f"\n📅 {page_date}")

            day_rows = self._process_single_day(
                code,
                page_date,
                time
            )

            month_rows.extend(day_rows)

        return month_rows

    def _prepare_month(self, year, month):

        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)

        self.loader._reset_row_tracker()
        self.calendar.open_calendar()
        print("   📂 Calendar opened")

        self.calendar.goto_month_year(year, month)
        print(f"   📆 Switched to {year}-{month:02d}")

    def _process_single_day(self, code, page_date, time_module):

        # --- open calendar and click day ---
        self.loader._reset_row_tracker()
        self.calendar.open_calendar()

        print("   👉 Clicking calendar day...")
        self.calendar.click_calendar_day(page_date)

        # --- wait overlay ---
        self.loader.wait_overlay_clear()
        print("   ✅ Overlay cleared")

        self.page.wait_for_timeout(800)

        before_rows = self._get_row_count()
        print(f"   📦 Rows after day click: {before_rows}")

        # --- load full list ---
        print("   🚀 Enter ensure_all_rows_loaded")
        self.loader.ensure_all_rows_loaded()
        print("   🏁 Exit ensure_all_rows_loaded")

        self.loader.wait_list_stable()
        print("   ✅ List stable")

        after_rows = self._get_row_count()
        print(f"   📊 Rows before parse: {after_rows}")

        snapshot = self.snapshot_flights()

        print("   🔍 Start parse_arrivals")

        day_rows = self.parser.parse_arrivals(
            code,
            page_date.isoformat(),
            snapshot
        )

        print("   ✅ parse_arrivals finished")

        scraped = len(day_rows)
        print(f"   📌 Parsed rows: {scraped}")

        export_day_debug(
            day_rows,
            code,
            page_date.isoformat(),
            "arrivals"
        )

        # --- safety reset ---
        reloaded = self.reset_if_large_dataset(after_rows)

        if reloaded:
            print("   ⏭ Skipping to next day after reload")
            return []

        time_module.sleep(1.2)

        return day_rows

    def _get_row_count(self):
        return self.page.locator(
            "li.ff-li-list.deparr"
        ).count()

# =========================
# SCRAPE
# =========================

    def scrape_airport(self, code, start_date, end_date):

        self._open_airport_page(code)

        all_rows = []
        current_month = start_date.replace(day=1)

        while current_month <= end_date:

            month_rows = self.scrape_current_month(
                code,
                current_month,
                start_date,
                end_date
            )

            all_rows.extend(month_rows)

            next_month = current_month + timedelta(days=32)
            current_month = next_month.replace(day=1)

        print(f"\n✅ DONE | TOTAL ROWS: {len(all_rows)}")
        return all_rows
