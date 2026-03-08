from datetime import timedelta , datetime , date
import os
import pandas as pd
import time
from services.calendar_service import DeterministicCalendarService
from services.loader_service import LoaderService
from services.parser_service import ParserService
from services.pageGuard_service import PageGuardService
from settings import SCRAPER_SETTINGS
from utils.exporter import (
    append_day_rows,
    append_week_rows,
    append_month_rows,
    append_year_rows,
    export_week_debug_pick,
    reset_daily_export_tracker,
)
from utils.validator import runcheck_and_report
class AirportScraper:

    def __init__(self, page):
        self.page = page

        self.loader = LoaderService(page)
        self.guard = PageGuardService(page)
        self.export_mode = SCRAPER_SETTINGS.get("export_mode", "day")
        self.calendar = DeterministicCalendarService(
            page,
            self.guard
        )

        self.parser = ParserService(
            page,
            self.loader,
            self.guard,
            settings=SCRAPER_SETTINGS
        )
        self.processed_days = 0
        df = pd.read_csv(self._resolve_airport_csv_path())
        self.airport_map = {
            row["airport_code"]: row["country"]
            for _, row in df.iterrows()
        }        


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

    def _resolve_airport_csv_path(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base_dir, "data", "reference", "world_airports_city.csv"),
            os.path.join(base_dir, "..", "data", "reference", "world_airports_city.csv"),
            os.path.join("data", "reference", "world_airports_city.csv"),
            os.path.join("..", "data", "reference", "world_airports_city.csv"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        raise FileNotFoundError(
            "world_airports_city.csv not found. tried: "
            + ", ".join(candidates)
        )

    def _format_date(self, date_text):
        dt = datetime.strptime(date_text, "%A, %d %B, %Y")
        return dt.strftime("%Y-%m-%d")

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

        # print(f"Processing month: {current_month.strftime('%Y-%m')}")

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
        if month_rows and self.export_mode != "day":
            self._export_by_mode(code, month_rows, current_month)


        return month_rows

    def _prepare_month(self, year, month):

        # self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)

        self.loader._reset_row_tracker()
        # print("   📂 Calendar opened")
        # print(f"🧪 PREPARE MONTH {year}-{month:02d}")

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

    def _run_arrival_loop(self, code, days_in_week, week_rows, week_debug_pick):

        # print("📦 WEEK PASS: ARRIVAL")

        for day in days_in_week:

            rows = self._run_day_pass(
                code,
                day,
                direction="arrival"
            )

            week_rows.extend(rows)

            kill_count = getattr(self.parser, "footer_kill_count", 0)

        if kill_count >= week_debug_pick["arrival"].get("kill", 0):
            week_debug_pick["arrival"] = {
                "day": day,
                "rows": rows,
                "kill": kill_count
            }

    def _run_departure_loop(self, code, days_in_week, week_rows, week_debug_pick):

        print("🔄 switch -> departure")
        self._switch_direction_tab("departure")

        # print("📦 WEEK PASS: DEPARTURE")

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

        if kill_count >= week_debug_pick["arrival"].get("kill", 0):
            week_debug_pick["departure"] = {
                "day": day,
                "rows": rows,
                "kill": kill_count
            }

    def _switch_direction_tab(self, target):
        # print("   👉 before switch")
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

        # print(f"   🔁 tab switched: {before_sort} → {after_sort}")

        self.loader.wait_list_stable()
        # print("   👉 after switch")
        # =========================
        # NEW: calendar state changed
        # =========================
        self.calendar._resolve_used = False

        # print("   🏁 TAB SWITCH DONE")

    def _run_day_pass(
        self,
        code,
        page_date,
        direction="arrival"
    ):
        # start-of-day: clear accumulators when direction is arrival
        if direction == "arrival":
            self._day_expected_arrival = 0
            self._day_expected_departure = 0

        # t0 = time.perf_counter()

        self.loader._reset_row_tracker()

        if not self.calendar.resolve_target_date(page_date):
            print("   ⏭️ skip date (cannot select)")
            return []

        # t0 = time.perf_counter()

        self.loader.wait_overlay_clear()
        # t_overlay = time.perf_counter()

        if self.loader._is_empty_result():
            # dt = time.perf_counter() - t0
            print(f"      🟢 empty day done ")
            return []

        self.loader.wait_overlay_then_rows()
        # t_rows = time.perf_counter()


        page_date_label = self._get_page_date_label()

        mode = SCRAPER_SETTINGS.get("export_mode", "month")
        print(f"   ▶ : {direction.upper()}  : Tab  |  🏍️_. EXPORT MODE : {mode.upper()}")

        rows, expected_info = self._run_direction_pass(
            code,
            page_date_label,
            direction=direction
        )

        # normalize expected info (support int or dict)
        if isinstance(expected_info, dict):
            expected_count = int(expected_info.get("count", 0))
            expected_scope = expected_info.get("scope", "unknown")
        else:
            expected_count = int(expected_info or 0)
            expected_scope = "unknown"

        # accumulate expected counts
        if not hasattr(self, '_day_expected_arrival'):
            self._day_expected_arrival = 0
        if not hasattr(self, '_day_expected_departure'):
            self._day_expected_departure = 0

        if direction == "arrival":
            # arrival page returns arrival count directly
            self._day_expected_arrival = expected_count or 0
        else:
            # Use the page-provided departure value directly (do not derive by subtraction)
            self._day_expected_departure = expected_count or 0

        total_expected = self._day_expected_arrival + self._day_expected_departure

        if self.export_mode == "day" and rows:
            date_key = self._format_date(page_date_label)
            country = self.airport_map.get(code, "UNKNOWN")

            csv_path, first = append_day_rows(
                rows,
                country,
                code,
                date_key,
                expected_count=total_expected,
                expected_arrival=self._day_expected_arrival,
                expected_departure=self._day_expected_departure
            )

            # run post-export report only on append
            if (
                SCRAPER_SETTINGS.get("post_export_report_enabled")
                and csv_path
                and not first
            ):
                try:
                    runcheck_and_report(csv_path, expected_count=total_expected)
                except Exception:
                    pass
        # dt = time.perf_counter() - t0
        # print(f"      ⏱ overlay: {t_overlay - t0:.2f}s")
        # print(f"      ⏱ rows: {t_rows - t_overlay:.2f}s")


        return rows

    def _run_direction_pass(
        self,
        code,
        page_date_label,
        direction
    ):

        # ✅ รอ overlay อย่างเดียว
        self.loader.wait_overlay_clear()

        # ✅ ถ้า tab นี้ empty → จบเลย
        if self.loader._is_empty_result():
            print(f"      ⏭️ skip parse ({direction} empty)")
            return [], {"count": 0, "scope": "unknown"}

        # ✅ ค่อยโหลด rows
        self.loader.ensure_all_rows_loaded()

        self.loader.wait_list_stable()

        # grab expected count from page text (arrivals or departures)
        try:
            expected_info = self.loader.get_expected_rows()
            if isinstance(expected_info, dict):
                expected = int(expected_info.get("count", 0))
                scope = expected_info.get("scope", "unknown")
            else:
                expected = int(expected_info or 0)
                scope = "unknown"
            expected = {"count": expected, "scope": scope}
        except:
            expected = {"count": 0, "scope": "unknown"}

        # if the reported number disagrees with the number of elements we have
        # actually loaded, prefer the actual count. log a warning for diagnostics.
        actual = self.loader._get_current_row_count()
        if actual != expected.get("count", 0):
            print(
                f"   ⚠ expected mismatch ({scope}): page {expected.get('count')} vs DOM {actual}, using DOM" \
            )
            expected = {"count": actual, "scope": scope}

        snapshot = self.snapshot_flights()

        print(f"   🔍 Start parse ({direction})")

        rows = self.parser.parse_list(
            code,
            page_date_label,
            snapshot,
            direction=direction
        )

        return rows, expected

    def _process_week_block(
        self,
        code,
        days_in_week,
        settings
    ):
        """
        Process one weekly batch using project settings.
        """

        # -------------------------
        # DEBUG 
        # -------------------------
        # print("\n🧪 WEEK DEBUG")
        # print("   len(days_in_week):", len(days_in_week))
        # print("   days:", days_in_week)

        # =========================
        # SMART WEEK CHECK
        # =========================
        self.calendar.goto_month_year(
            days_in_week[0].year,
            days_in_week[0].month
        )

        # ⭐ single-day week bypass
        if len(days_in_week) == 1:
            print("🟡 single-day week → bypass week scan")

        else:
            if not self.calendar.week_has_selectable_day(days_in_week):
                print("⏭️ WEEK EMPTY → skip (no tab switch)")
                return []

        week_rows = []
        week_debug_combined = {
            "day": None,
            "rows": [],
            "kill": 0
        }
        # -------------------------
        # WEEK DEBUG PICK
        # -------------------------
        week_debug_pick = {
            
            "arrival": {
                "day": None,
                "rows": None,
                "kill": 0
            },
            "departure": {
                "day": None,
                "rows": None,
                "kill": 0
            }
        }



        # =========================
        # ARRIVAL PASS
        # =========================
        if settings["arrival_parser_enabled"]:

            # print("📦 WEEK PASS: ARRIVAL")

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

                # ⭐ NEW: รวม debug
                week_debug_combined["rows"].extend(rows)

                if kill_count >= week_debug_combined["kill"]:
                    week_debug_combined["kill"] = kill_count
                    week_debug_combined["day"] = day

                # (ถ้ายังอยากเก็บ debug_pick เดิมไว้)
                if kill_count >= week_debug_pick["arrival"].get("kill", 0):
                    week_debug_pick["arrival"] = {
                        "day": day,
                        "rows": rows,
                        "kill": kill_count
                    }


        # =========================
        # DEPARTURE PASS
        # =========================
        if settings["departure_parser_enabled"]:

            self._switch_direction_tab("departure")

            # print("📦 WEEK PASS: DEPARTURE")

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

                # ⭐ NEW: รวม debug
                week_debug_combined["rows"].extend(rows)

                if kill_count >= week_debug_combined["kill"]:
                    week_debug_combined["kill"] = kill_count
                    week_debug_combined["day"] = day

                # (ถ้ายังอยากเก็บ debug_pick เดิมไว้)
                if kill_count >= week_debug_pick["departure"].get("kill", 0):
                    week_debug_pick["departure"] = {
                        "day": day,
                        "rows": rows,
                        "kill": kill_count
                    }


        # =========================
        # OPTIONAL RESTORE
        # =========================
        if settings.get("auto_restore_tab", True):
            # print("🔄 restore -> arrival")
            self._switch_direction_tab("arrival")

        # =========================
        # EXPORT WEEK DEBUG
        # =========================
        if settings.get("debug_week_export", True):

            export_week_debug_pick(
                week_debug_combined,
                code
            )

        return week_rows

    def _export_by_mode(self, code, rows, current_month):

        if not rows:
            return

        mode = SCRAPER_SETTINGS.get("export_mode", "month")
        country = self._get_country_from_code(code)

        # =========================
        # DAY MODE
        # =========================
        if mode == "day":

            by_day = {}

            for r in rows:
                d = r.get("date")
                if not d:
                    continue

                by_day.setdefault(d, []).append(r)

            for d, day_rows in by_day.items():

                # 🔥 format ป้องกัน /
                safe_date = datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d")

                append_day_rows(
                    day_rows,
                    country,
                    code,
                    safe_date
                )

        # =========================
        # WEEK MODE
        # =========================
        elif mode == "week":

            week_key = current_month.strftime("%Y-W%U")

            append_week_rows(
                rows,
                country,
                code,
                week_key
            )

        # =========================
        # YEAR MODE
        # =========================
        elif mode == "year":

            year_key = str(current_month.year)

            append_year_rows(
                rows,
                country,
                code,
                year_key
            )

        # =========================
        # MONTH MODE
        # =========================
        else:

            month_key = current_month.strftime("%Y-%m")

            append_month_rows(
                rows,
                country,
                code,
                month_key
            )

# =========================
# SCRAPE
# =========================

    def scrape_airport(self, code, start_date, end_date):

        self._open_airport_page(code)
        reset_daily_export_tracker()
        mode = SCRAPER_SETTINGS.get("export_mode", "month")
        print(f"\n🏍️_. EXPORT MODE : {mode.upper()}")
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

    def _get_country_from_code(self, code):
        return self.airport_map.get(code, "Unknown")
