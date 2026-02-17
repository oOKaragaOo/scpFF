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

    def parse_arrivals(
    self,
    arrival_airport,
    current_date,
    snapshot_flights,
    direction="arrival"
):  

        snapshot_flights = set(snapshot_flights)
        rows = []

        self.guard.ensure_vue_ready(self.loader)

        elements = self._snapshot_elements()

        footer_kill_count = 0

        pbar = tqdm(
            elements,
            desc="   Row runing : ",
            ascii=("_", "▄"),
            colour="#83f77e",
            unit="flight",
            ncols=150
        )

        for el in pbar:

            try:
                row_data = self._parse_single_element(
                                el,
                                arrival_airport,
                                current_date,
                                direction
                            )

                # ⭐ update safe handle ทุกครั้งที่ success
                self.safe_handle = el

                if row_data:
                    rows.append(row_data)

                pbar.set_postfix_str(
                    f"Footer Kill : {footer_kill_count}"
                )

            except Exception:

                revived = self.recover_from_footer_only()
                if revived:
                    footer_kill_count += 1

                pbar.set_postfix_str(
                    f"Footer Kill : {footer_kill_count}"
                )

                # self._close_popup()
                continue

        rows = self.recover_missing_flights(
            arrival_airport,
            current_date,
            snapshot_flights,
            rows,
            direction=direction
        )

        # ⭐ summary ต่อวัน
        # print(f"   ☠️ Footer Kill Total: {footer_kill_count}")
        self._close_popup()
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

    def _parse_single_element(
    self,
    el,
    arrival_airport,
    current_date,
    direction="arrival"
):

        self.guard.ensure_page_clean()

        btn = el.query_selector(".flightsfrom-list-money")
        self.page.evaluate("(e) => e.click()", btn)

        # self.page.wait_for_timeout(100)
        if self.page.locator(".uk-grid").count() <= 2:
            raise Exception("footer_only_detected")
        popup = self._open_popup()
        if self.safe_handle is None:
            self.safe_handle = el
        row = {
            "airport": arrival_airport,
            "direction": direction,
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

        # self._close_popup()

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
        try:
            btn = self.page.locator("#ff-day-infobox .ff-day-close")  # เปลี่ยน selector ตามจริง
            if btn.count():
                btn.first.click(force=True)
        except:
            pass

        # self.page.wait_for_timeout(120)

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
        parsed_rows,
        direction="arrival" 
    ):

        parsed_set = {r["flight"] for r in parsed_rows}
        missing = list(set(snapshot_flights) - parsed_set)

        if not missing:
            return parsed_rows

        recovered_count = 0

        self.loader.ensure_all_rows_loaded()
        self.loader.wait_list_stable()

        pbar = tqdm(
            missing,
            desc="     Recovery : ",
            ascii=("_", "▄"),
            colour="#f7d983",
            unit="flight",
            ncols=150
        )

        for flight_code in pbar:

            try:
                self.recover_from_footer_only()
                self.guard.ensure_vue_ready(self.loader)

                row = self._find_row_by_flight_code(flight_code)
                if row is None:
                    continue

                row_data = {
                    "airport": arrival_airport,
                    "direction": direction,
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
                recovered_count += 1

            except Exception:
                continue

            # ⭐ summary realtime (line เดียว)
            pbar.set_postfix_str(
                f"Recovered: {recovered_count}/{len(missing)} | Total: {len(parsed_rows)}"
            )

        # ----------------------------
        # SUMMARY
        # ----------------------------
        print(
            f"   ✅ Recovery done | "
            f"Recovered: {recovered_count}/{len(missing)} | "
            f"Final rows: {len(parsed_rows)}"
        )
        self._close_popup()
        return parsed_rows

# =========================
# Footer-only Recovery
# =========================

    def recover_from_footer_only(self):

        try:
            grid = self.page.locator(".uk-grid").count()
            rows = self.page.locator("li.ff-li-list.deparr").count()

            # หน้าไม่พัง
            if grid > 2 and rows > 0:
                return False

            if not self.safe_handle:
                return False

            btn = self.safe_handle.query_selector(".flightsfrom-list-money")

            # soft revive click
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

            if grid_after > 2 and rows_after > 0:
                return True

            return False

        except Exception:
            return False

# =========================
# Refactoring
# =========================

    def parse_list(
        self,
        arrival_airport,
        current_date,
        snapshot_flights,
        direction="arrival"
    ):
        """
        Temporary wrapper for refactor phase.
        Keeps old behavior unchanged.
        """

        # ❗ยังใช้ logic เดิมทั้งหมด
        return self.parse_arrivals(
            arrival_airport,
            current_date,
            snapshot_flights,
            direction=direction
        )

