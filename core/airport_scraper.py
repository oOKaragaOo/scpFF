from datetime import timedelta , datetime , date
# from services.calendar_service import CalendarService
from services.calendar_service import DeterministicCalendarService
from services.loader_service import LoaderService
from services.parser_service import ParserService
from services.pageGuard_service import PageGuardService
from settings import SCRAPER_SETTINGS
from utils.exporter import (
    export_week_debug_pick,
    append_month_rows,
    export_day_debug
)
class AirportScraper:

    def __init__(self, page):
        self.page = page

        self.loader = LoaderService(page)
        self.guard = PageGuardService(page)

        # ⭐ ต้องส่ง guard เข้าไป
        self.calendar = DeterministicCalendarService(
            page,
            self.guard
        )

        self.parser = ParserService(
            page,
            self.loader,
            self.guard
        )


# =========================
# PRIVATE HELPERS
# =========================

    def _get_sorting_value(self):
        """
        ดึงค่า sorting จาก URL
        เช่น arrival-time / departure-time
        """
        from urllib.parse import urlparse, parse_qs

        url = self.page.url
        qs = parse_qs(urlparse(url).query)

        sorting = qs.get("sorting", [""])[0]
        return sorting


    def _format_date(self, date_text):
        dt = datetime.strptime(date_text, "%A, %d %B, %Y")
        return f"{dt.day}/{dt.month}/{dt.year}"

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

        # print(f"   📸 Snapshot DOM count: {dom_count}")
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

        from datetime import timedelta
        from utils.exporter import append_month_rows

        year = current_month.year
        month = current_month.month

        month_rows = []

        print(f"Processing month: {current_month.strftime('%Y-%m')}")

        self._prepare_month(year, month)

        # =========================
        # BUILD DAY LIST (SAFE)
        # =========================
        days = []

        cursor = start_date

        while cursor <= end_date:

            # keep only target month
            if cursor.year == year and cursor.month == month:
                days.append(cursor)

            cursor += timedelta(days=1)

        # =========================
        # WEEKLY BATCH LOOP
        # =========================
        idx = 0

        while idx < len(days):

            week_days = days[idx: idx + 7]

            if not week_days:
                break

            print(
                f"\n📦 WEEK BLOCK: "
                f"{week_days[0]} → {week_days[-1]}"
            )

            week_rows = self._process_week_block(
                code,
                week_days,
                settings=SCRAPER_SETTINGS
            )


            month_rows.extend(week_rows)

            idx += 7

        # =========================
        # EXPORT MONTH (FINAL)
        # =========================
        if month_rows:

            month_key = current_month.strftime("%Y-%m")

            append_month_rows(
                month_rows,
                code,
                month_key
            )

        return month_rows

    def _prepare_month(self, year, month):

        # self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)

        self.loader._reset_row_tracker()
        # print("   📂 Calendar opened")

        self.calendar.goto_month_year(year, month)
        # print(f"   📆 Switched to {year}-{month:02d}")

    def _get_row_count(self):
        return self.page.locator(
            "li.ff-li-list.deparr"
        ).count()

    def _get_page_date_label(self):

        container = self.page.locator(
            "a.select-date"
        ).locator("xpath=..")

        return container.inner_text().split("Select date")[0].strip()


    # def _process_single_day(self, code, page_date, time_module):

    #     self.loader._reset_row_tracker()

    #     if not self.calendar.resolve_target_date(page_date):
    #         print("   ⏭️ skip date (cannot select)")
    #         return []

    #     # self.loader.wait_overlay_clear()
    #     self.loader.wait_overlay_then_rows()

    #     page_date_label = self._get_page_date_label()

    #     print("   ▶ PASS: ARRIVAL")

    #     rows = self._run_direction_pass(
    #         code,
    #         page_date_label,
    #         direction="arrival"
    #     )

    #     return rows

    def _run_day_pass(
        self,
        code,
        page_date,
        direction="arrival"
    ):

        self.loader._reset_row_tracker()

        if not self.calendar.resolve_target_date(page_date):
            print("   ⏭️ skip date (cannot select)")
            return []

        self.loader.wait_overlay_then_rows()

        page_date_label = self._get_page_date_label()

        print(f"   ▶ PASS: {direction.upper()}")

        rows = self._run_direction_pass(
            code,
            page_date_label,
            direction=direction
        )

        return rows

    def _run_arrival_loop(self, code, days_in_week, week_rows, week_debug_pick):

        print("📦 WEEK PASS: ARRIVAL")

        for day in days_in_week:

            rows = self._run_day_pass(
                code,
                day,
                direction="arrival"
            )

            week_rows.extend(rows)

            kill_count = getattr(self.parser, "footer_kill_count", 0)

            if kill_count >= week_debug_pick["kill"]:
                week_debug_pick.update({
                    "day": day,
                    "rows": rows,
                    "kill": kill_count
                })

    def _run_departure_loop(self, code, days_in_week, week_rows, week_debug_pick):

        print("🔄 switch -> departure")
        self._switch_direction_tab("departure")

        print("📦 WEEK PASS: DEPARTURE")

        self.calendar.goto_month_year(
            days_in_week[0].year,
            days_in_week[0].month
        )

        for day in days_in_week:

            rows = self._run_day_pass(
                code,
                day,
                direction="departure"
            )

            week_rows.extend(rows)

            kill_count = getattr(self.parser, "footer_kill_count", 0)

            if kill_count >= week_debug_pick["kill"]:
                week_debug_pick.update({
                    "day": day,
                    "rows": rows,
                    "kill": kill_count
                })



    def _switch_direction_tab(self, target):

        print(f"\n🔄 SWITCH TAB -> {target}")

        current_sort = self._get_sorting_value()

        if target == "departure" and current_sort == "departure-time":
            print("   ⚡ already on departure (skip)")
            return

        if target == "arrival" and current_sort == "arrival-time":
            print("   ⚡ already on arrival (skip)")
            return

        before_sort = current_sort

        # --- logic switch เดิม ---
        self.parser._close_popup()
        self.parser.safe_handle = None
        self.loader._reset_row_tracker()

        tab = self.page.locator(
            f"div.shortcut-button:has(a:has-text('{ 'Arrivals' if target=='arrival' else 'Departures'}'))"
        )
        tab.first.click()

        self.page.wait_for_function(
            """
            (oldSorting) => {
                const url = new URL(window.location.href);
                return (url.searchParams.get("sorting") || "") !== oldSorting;
            }
            """,
            arg=before_sort,
            timeout=0
        )

        after_sort = self._get_sorting_value()

        print(f"   🔁 tab switched: {before_sort} → {after_sort}")

        self.loader.wait_list_stable()

        print("   🏁 TAB SWITCH DONE")

    def _run_day_pass(
        self,
        code,
        page_date,
        direction="arrival"
    ):

        self.loader._reset_row_tracker()

        if not self.calendar.resolve_target_date(page_date):
            print("   ⏭️ skip date (cannot select)")
            return []

        self.loader.wait_overlay_then_rows()

        page_date_label = self._get_page_date_label()

        print(f"   ▶ PASS: {direction.upper()}")

        rows = self._run_direction_pass(
            code,
            page_date_label,
            direction=direction
        )

        return rows


    def _process_week_block(
        self,
        code,
        days_in_week,
        settings
    ):
        """
        Process one weekly batch using project settings.

        settings example:
        {
            "arrival_parser_enabled": True,
            "departure_parser_enabled": True,
            "auto_restore_tab": True,
            "debug_week_export": True,
        }
        """

        # =========================
        # SMART WEEK CHECK
        # =========================
        self.calendar.goto_month_year(
            days_in_week[0].year,
            days_in_week[0].month
        )

        if not self.calendar.week_has_selectable_day(days_in_week):
            print("⏭️ WEEK EMPTY → skip (no tab switch)")
            return []

        week_rows = []

        # -------------------------
        # WEEK DEBUG PICK (1 file)
        # -------------------------
        week_debug_pick = {
            "day": None,
            "rows": None,
            "kill": -1
        }

        # =========================
        # ARRIVAL PASS
        # =========================
        if settings["arrival_parser_enabled"]:

            print("📦 WEEK PASS: ARRIVAL")

            for day in days_in_week:

                rows = self._run_day_pass(
                    code,
                    day,
                    direction="arrival"
                )

                week_rows.extend(rows)

                kill_count = getattr(
                    self.parser,
                    "footer_kill_count",
                    0
                )

                if kill_count >= week_debug_pick["kill"]:
                    week_debug_pick = {
                        "day": day,
                        "rows": rows,
                        "kill": kill_count
                    }

        # =========================
        # DEPARTURE PASS
        # =========================
        if settings["departure_parser_enabled"]:

            print("🔄 switch -> departure")
            self._switch_direction_tab("departure")

            print("📦 WEEK PASS: DEPARTURE")

            self.calendar.goto_month_year(
                days_in_week[0].year,
                days_in_week[0].month
            )

            for day in days_in_week:

                rows = self._run_day_pass(
                    code,
                    day,
                    direction="departure"
                )

                week_rows.extend(rows)

                kill_count = getattr(
                    self.parser,
                    "footer_kill_count",
                    0
                )

                if kill_count >= week_debug_pick["kill"]:
                    week_debug_pick = {
                        "day": day,
                        "rows": rows,
                        "kill": kill_count
                    }

        # =========================
        # OPTIONAL RESTORE
        # =========================
        if settings.get("auto_restore_tab", True):
            print("🔄 restore -> arrival")
            self._switch_direction_tab("arrival")

        # =========================
        # EXPORT WEEK DEBUG
        # =========================
        if settings.get("debug_week_export", True):
            export_week_debug_pick(
                week_debug_pick,
                code
            )

        return week_rows


    # def _process_week_block(
    #     self,
    #     code,
    #     days_in_week,
    #     run_arrival=True,
    #     run_departure=True,
    #     auto_restore=True,
    #     restore_to="arrival"
    # ):
    #     """
    #     Process one weekly batch (mode-based).

    #     MODE EXAMPLES
    #     ───────────────────────────────
    #     1) ARRIVAL ONLY
    #     run_arrival=True
    #     run_departure=False
    #     auto_restore=False

    #     2) DEPARTURE ONLY
    #     run_arrival=False
    #     run_departure=True
    #     auto_restore=False

    #     3) FULL MODE (production)
    #     run_arrival=True
    #     run_departure=True
    #     auto_restore=True
    #     restore_to="arrival"

    #     4) FULL MODE (stay on departure)
    #     restore_to="departure"
    #     """

    #     # =========================
    #     # SMART WEEK CHECK
    #     # =========================
    #     self.calendar.goto_month_year(
    #         days_in_week[0].year,
    #         days_in_week[0].month
    #     )

    #     if not self.calendar.week_has_selectable_day(days_in_week):
    #         print("⏭️ WEEK EMPTY → skip (no tab switch)")
    #         return []


    #     week_rows = []

    #     # -------------------------
    #     # WEEK DEBUG PICK (1 file)
    #     # -------------------------
    #     week_debug_pick = {
    #         "day": None,
    #         "rows": None,
    #         "kill": -1
    #     }

    #     # =========================
    #     # ARRIVAL PASS
    #     # =========================
    #     if run_arrival:

    #         print("📦 WEEK PASS: ARRIVAL")

    #         for day in days_in_week:

    #             rows = self._process_single_day(
    #                 code,
    #                 day,
    #                 __import__("time")
    #             )

    #             week_rows.extend(rows)

    #             kill_count = getattr(
    #                 self.parser,
    #                 "footer_kill_count",
    #                 0
    #             )

    #             if kill_count >= week_debug_pick["kill"]:
    #                 week_debug_pick = {
    #                     "day": day,
    #                     "rows": rows,
    #                     "kill": kill_count
    #                 }

    #     # =========================
    #     # DEPARTURE PASS
    #     # =========================
    #     if run_departure:

    #         print("🔄 switch -> departure")
    #         self._switch_direction_tab("departure")

    #         print("📦 WEEK PASS: DEPARTURE")
    #         self.calendar.goto_month_year(
    #             days_in_week[0].year,
    #             days_in_week[0].month)
    #         for day in days_in_week:

    #             self.loader._reset_row_tracker()

    #             if not self.calendar.resolve_target_date(day):
    #                 continue

    #             self.loader.wait_overlay_clear()

    #             page_date_label = self._get_page_date_label()

    #             rows = self._run_direction_pass(
    #                 code,
    #                 page_date_label,
    #                 direction="departure"
    #             )

    #             week_rows.extend(rows)

    #             kill_count = getattr(
    #                 self.parser,
    #                 "footer_kill_count",
    #                 0
    #             )

    #             if kill_count >= week_debug_pick["kill"]:
    #                 week_debug_pick = {
    #                     "day": day,
    #                     "rows": rows,
    #                     "kill": kill_count
    #                 }

    #     # =========================
    #     # OPTIONAL RESTORE
    #     # =========================
    #     if auto_restore:
    #         print(f"🔄 restore -> {restore_to}")
    #         self._switch_direction_tab(restore_to)

    #     # =========================
    #     # EXPORT WEEK DEBUG
    #     # =========================
    #     export_week_debug_pick(
    #         week_debug_pick,
    #         code
    #     )

    #     return week_rows

# =========================
# SCRAPE
# =========================

    def scrape_airport(self, code, start_date, end_date):

        self._open_airport_page(code)
        self.calendar.warmup_calendar(start_date)
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

    def _process_single_day_dryrun(self, code, page_date, time_module):

        # --- test only: no scraping ---
        self.loader._reset_row_tracker()

        # print("   👉 Clicking calendar day...")
        # time.sleep(2)
        if not self.calendar.resolve_target_date(page_date):
            print("   ⏭️ skip date (cannot select)")
            return []

        print("   🧪 DRY RUN: click success (no scraping)")
        return []

