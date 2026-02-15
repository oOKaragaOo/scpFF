from tqdm import tqdm
import time
from datetime import datetime 
class ParserService:

    def __init__(self, page, loader,guard):
        self.page = page
        self.loader = loader
        self.guard = guard
        self.safe_handle = None
    
    # =========================
    # Main Parse
    # =========================

    def parse_arrivals(self, arrival_airport, current_date, snapshot_flights):

        snapshot_flights = set(snapshot_flights)
        rows = []
                

        self.guard.ensure_vue_ready(self.loader)


        elements = self._snapshot_elements()

        for el in tqdm(elements,
               desc="Row runing : ",
               ascii=("_", "▄"),
               colour="#83f77e",
               unit="flight",
               ncols=120):

            try:
                row_data = self._parse_single_element(
                    el,
                    arrival_airport,
                    current_date
                )
                if row_data:
                    rows.append(row_data)

            except Exception as e:
                try:
                    f = el.locator(".deparr_flight").inner_text()
                except:
                    f = "UNKNOWN"
                    print(f"   ❌ Parse fail: {f} | {e}")
                self._close_popup()
                continue



        parsed_set = {r["flight"] for r in rows}
        # print(f"   📊 Parsed unique flights: {len(parsed_set)}")

        rows = self.recover_missing_flights(
            arrival_airport,
            current_date,
            snapshot_flights,
            rows
        )

        return rows

    # =========================
    # Snapshot
    # =========================

    def _snapshot_elements(self):
        locator = self.page.locator("li.ff-li-list.deparr")
        total = locator.count()

        elements = []
        for i in range(total):
            elements.append(locator.nth(i).element_handle())

        return elements

    def _parse_single_element(self, el, arrival_airport, current_date):

        self.guard.ensure_page_clean()

        btn = el.query_selector(".flightsfrom-list-money")
        self.page.evaluate("(e) => e.click()", btn)

        popup = self._open_popup()
        if self.safe_handle is None:
            self.safe_handle = el
        row = {
            "airport": arrival_airport,
            "direction": "arrival",
            "date": self._format_date(current_date),
            "day_name": current_date.split(",")[0],
            "time": el.query_selector(".deparr_time div").inner_text(),
            "flight": el.query_selector(".deparr_flight").inner_text(),
            "airline": el.query_selector(".deparr_airline_name").inner_text(),
            "duration": el.query_selector(".deparr_duration").inner_text(),

            # meta
            "airline_source": "text",
            "page_date_verified": True,
            "scraped_at": datetime.utcnow().isoformat()
        }

        row.update(self._extract_popup_data(popup))

        uid = self._make_uid(
            current_date,
            row["flight"],
            row.get("time_range")
        )

        row["uid"] = uid

        self._close_popup()

        return row

    # =========================
    # Popup Control
    # =========================

    def _open_popup(self):
        self.page.wait_for_function(
            "() => document.querySelector('#ff-day-infobox')?.innerText.length > 20",
            timeout=4000
        )
        return self.page.locator("#ff-day-infobox")

    def _extract_popup_data(self, popup):

        def get_val(label):
            el = popup.locator(
                f"div.ff-font-s.uk-flex:has(div.ff-font-strong:text-is('{label}')) div.uk-text-right"
            )
            return el.inner_text() if el.count() else None

        time_range_el = popup.locator("div.ff-font-m.ff-font-bold").first
        time_range = time_range_el.inner_text() if time_range_el.count() else None

        return {
            "time_range": time_range,
            "distance": get_val("Distance"),
            "aircraft": get_val("Aircraft"),
            "seats": get_val("Seats"),
            "codeshare": get_val("Codeshare"),
            "meals": get_val("Meals"),
        }

    def _close_popup(self):
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(120)

    # =========================
    # Recovery
    # =========================
    def _format_date(self, date_text):
        dt = datetime.strptime(date_text, "%A, %d %B, %Y")
        return f"{dt.day}/{dt.month}/{dt.year}"

    def _compact_time_range(self, time_text):
        return (
            time_text
            .replace(":", "")
            .replace(" ", "")
            .replace("-", "")
        )

    def _short_date(self, date_text):
        dt = datetime.strptime(date_text, "%A, %d %B, %Y")
        return dt.strftime("%y%m%d")

    def _find_row_by_flight_code(self, flight_code):

        rows = self.page.locator("li.ff-li-list.deparr")
        total = rows.count()

        if total == 0:
            return None

        for i in range(total):

            candidate = rows.nth(i)

            try:
                text = candidate.locator(
                    ".deparr_flight"
                ).inner_text().strip()

                # ⭐ normalize กัน text แถม
                first_token = text.split()[0]

                if first_token == flight_code:
                    return candidate

            except:
                continue

        return None

    def _make_uid(self, current_date, flight, time_range):

        if not time_range:
            return ""

        d = self._short_date(current_date)
        t = self._compact_time_range(time_range)

        return f"{d}_{flight}_{t}"

    def recover_missing_flights(
        self,
        arrival_airport,
        current_date,
        snapshot_flights,
        parsed_rows
    ):

        parsed_set = {r["flight"] for r in parsed_rows}
        missing = set(snapshot_flights) - parsed_set

        if not missing:
            return parsed_rows

        print(f"   🔎 Recovery pass → {len(missing)} flights missing")

        self.loader.ensure_all_rows_loaded()
        self.loader.wait_list_stable()

        for flight_code in missing:

            try:

                self.recover_from_footer_only()

                self.guard.ensure_vue_ready(self.loader)

                row = self._find_row_by_flight_code(flight_code)
                if row is None:
                    continue

                # LIST ONLY
                row_data = {
                    "airport": arrival_airport,
                    "direction": "arrival",
                    "date": self._format_date(current_date),
                    "day_name": current_date.split(",")[0],

                    "time": row.locator(".deparr_time div").inner_text(),
                    "flight": flight_code,
                    "airline": row.locator(".deparr_airline_name").inner_text(),
                    "duration": row.locator(".deparr_duration").inner_text(),

                    "airline_source": "no have detail",
                    "page_date_verified": True,
                    "scraped_at": datetime.utcnow().isoformat(),

                    "time_range": "",
                    "distance": "",
                    "aircraft": "",
                    "seats": "",
                    "codeshare": "",
                    "meals": "",
                    "entertainment": ""
                }

                row_data["uid"] = self._make_uid(
                    current_date,
                    row_data["flight"],
                    row_data.get("time_range")
                )

                parsed_rows.append(row_data)

            except Exception:
                continue

        # =====================================================
        # FINAL CHECK → click missing flights for logging only
        # =====================================================
        print("   🧪 Final click check")

        for flight_code in missing:

            try:
                self.recover_from_footer_only()

                row = self._find_row_by_flight_code(flight_code)
                if row is None:
                    print(f"   ⚠️ {flight_code} not found")
                    continue

                btn = row.locator(".flightsfrom-list-money")

                if btn.count():
                    btn.click(force=True)
                    print(f"   🟢 Click OK: {flight_code}")

                    self._close_popup()

            except Exception as e:
                print(f"   🔴 Click fail: {flight_code} | {e}")

                try:
                    self._close_popup()
                except:
                    pass

        print(f"   ✅ After recovery → {len(parsed_rows)} rows")
        return parsed_rows

# =========================
# Footer-only Recovery (use parser timeout behavior)
# =========================

# =========================
# Footer-only Recovery
# =========================
    def recover_from_footer_only(self):

        try:
            grid = self.page.locator(".uk-grid").count()
            rows = self.page.locator("li.ff-li-list.deparr").count()

            if grid > 2 and rows > 0:
                return False

            print("   💀 Footer-only detected → revive click")

            # ---------------------------------
            # ใช้ SAFE HANDLE
            # ---------------------------------
            if not self.safe_handle:
                print("   ⚠️ No safe handle")
                return False

            btn = self.safe_handle.query_selector(".flightsfrom-list-money")
            self.page.evaluate("""
                (e) => {
                    e.dispatchEvent(new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    }));
                }
                """, btn)

            self.page.wait_for_timeout(300)

            grid_after = self.page.locator(".uk-grid").count()
            rows_after = self.page.locator("li.ff-li-list.deparr").count()

            print(f"   🔎 AFTER REVIVE  | grid={grid_after} rows={rows_after}")

            if grid_after > 2 and rows_after > 0:
                print("   ♻️ Back to list")
                return True

            print("   ⚠️ Still footer-only")
            return False

        except Exception:
            return False
