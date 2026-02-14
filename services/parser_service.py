from tqdm import tqdm

class ParserService:

    def __init__(self, page, loader,guard):
        self.page = page
        self.loader = loader
        self.guard = guard

    # =========================
    # Vue Guard move to guard class
    # =========================

    # def is_vue_unmounted(self):
    #     return self.page.evaluate("""
    #     () => {
    #         const rows = document.querySelectorAll('li.ff-li-list.deparr');
    #         if (!rows || rows.length === 0) return true;

    #         const list = document.querySelector('ul.ff-list');
    #         if (!list) return true;

    #         return false;
    #     }
    #     """)

    # def wait_vue_stable(self, timeout=5000):
    #     self.page.wait_for_function(
    #         """() => {
    #             const rows = document.querySelectorAll('li.ff-li-list.deparr');
    #             return rows && rows.length > 0;
    #         }""",
    #         timeout=timeout
    #     )

    # def _ensure_vue_ready(self):
    #     self.page.keyboard.press("Escape")

    #     if self.is_vue_unmounted():
    #         self.wait_vue_stable()

    #     self.loader.wait_list_stable()

    # =========================
    # Main Parse
    # =========================

    def parse_arrivals(self, arrival_airport, current_date, snapshot_flights):

        snapshot_flights = set(snapshot_flights)
        rows = []

        self.guard.ensure_vue_ready(self.loader)


        elements = self._snapshot_elements()

        for el in tqdm(elements,
               desc="Row scraping : ",
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

            except Exception:
                self._close_popup()
                continue

        parsed_set = {r["flight"] for r in rows}
        print(f"   📊 Parsed unique flights: {len(parsed_set)}")

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

    # =========================
    # Single Row Parse
    # =========================

    def _parse_single_element(self, el, arrival_airport, current_date):

        self.guard.ensure_page_clean()

        btn = el.query_selector(".flightsfrom-list-money")
        self.page.evaluate("(e) => e.click()", btn)

        popup = self._open_popup()

        row = {
            "arrival_airport": arrival_airport,
            "date": current_date,
            "arrival_time": el.query_selector(".deparr_time div").inner_text(),
            "flight": el.query_selector(".deparr_flight").inner_text(),
            "airline": el.query_selector(".deparr_airline_name").inner_text(),
            "duration": el.query_selector(".deparr_duration").inner_text(),
        }

        row.update(self._extract_popup_data(popup))

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

        return {
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

        self.loader.wait_list_stable()

        for flight_code in missing:

            try:
                self.guard.ensure_page_clean()

                row = self._find_row_by_flight_code(flight_code)

                if row is None:
                    continue

                arrival_time = row.locator(".deparr_time div").inner_text()
                airline = row.locator(".deparr_airline_name").inner_text()
                duration = row.locator(".deparr_duration").inner_text()

                btn = row.locator(".flightsfrom-list-money")
                btn.click(force=True)

                popup = self._open_popup()

                parsed_rows.append({
                    "arrival_airport": arrival_airport,
                    "date": current_date,
                    "arrival_time": arrival_time,
                    "flight": flight_code,
                    "airline": airline,
                    "duration": duration,
                    **self._extract_popup_data(popup)
                })

                self._close_popup()
                self.loader.wait_list_stable()

            except Exception:
                self._close_popup()
                continue

        print(f"   ✅ After recovery → {len(parsed_rows)} rows")

        return parsed_rows

    def _find_row_by_flight_code(self, flight_code):

        candidates = self.page.locator(
            "li.ff-li-list.deparr"
        ).filter(
            has=self.page.locator(".deparr_flight", has_text=flight_code)
        )

        if candidates.count() == 0:
            return None

        for i in range(candidates.count()):
            candidate = candidates.nth(i)
            text = candidate.locator(".deparr_flight").inner_text().strip()
            if text == flight_code:
                return candidate

        return None
