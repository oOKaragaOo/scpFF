# =========================
# BLOCK ADS / IFRAME
# =========================
def kill_overlays(page):
    page.evaluate("""
    () => {

        // =========================
        // 1️⃣ ปิด inactivity แบบถูกต้อง
        // =========================
        const idleOverlay = document.getElementById('ff-idle-overlay');
        if (idleOverlay && idleOverlay.style.display === 'block') {
            if (typeof closeInactivityAd === 'function') {
                closeInactivityAd();
            } else {
                idleOverlay.style.display = 'none';
            }
        }

        // =========================
        // 2️⃣ ปิด idle ad container ถ้ามี
        // =========================
        const idleAd = document.getElementById('ff-idle-ad');
        if (idleAd) {
            const closeBtn = idleAd.querySelector('.ad-container-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }

        // =========================
        // 3️⃣ ลบเฉพาะ external ads จริง ๆ
        // =========================
        const adSelectors = [
            '.ff-phone-ad',
            '.phone-ad-show-switch',
            'iframe[src*="doubleclick"]',
            'iframe[src*="googlesyndication"]',
            'iframe[src*="adservice"]',
            'iframe[src*="adsystem"]',
            'iframe[src*="taboola"]',
            'iframe[src*="outbrain"]',
            'iframe[src*="facebook"]'
        ];

        adSelectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });

        // =========================
        // 4️⃣ unlock scroll แบบปลอดภัย
        // =========================
        document.documentElement.style.overflow = '';
        document.body.style.overflow = '';
        document.body.style.pointerEvents = '';
        document.body.classList.remove('uk-modal-page');
    }
    """)

def unlock_page(page):
    page.evaluate("""
    () => {
        document.documentElement.style.overflow = 'auto';
        document.body.style.overflow = 'auto';
        document.body.classList.remove('uk-modal-page');
    }
    """)

def overlay_detected(page):
    return page.evaluate("""
    () => !!(
        document.querySelector('#ff-idle-ad') ||
        document.querySelector('.ff-footer') ||
        document.body.style.overflow === 'hidden'
    )
    """)

def ensure_page_clean(page):
    if  overlay_detected(page):
        kill_overlays(page)
        unlock_page(page)

def block_ads(route):
    url = route.request.url
    if any(x in url for x in [
        "doubleclick", "googlesyndication", "adservice",
        "adsystem", "taboola", "outbrain", "facebook"
    ]):
        route.abort()
    else:
        route.continue_()

def close_idle_ad(page):
    try:
        ad = page.locator("#ff-idle-ad")
        if ad.count() > 0 and ad.is_visible():
            close_btn = ad.locator(".ad-container-close")
            if close_btn.count() > 0:
                close_btn.click(force=True)
                page.wait_for_timeout(300)
    except:
        pass



class ParserService:
    def is_vue_unmounted(self):
        return self.page.evaluate("""
        () => {
            const rows = document.querySelectorAll('li.ff-li-list.deparr');
            if (!rows || rows.length === 0) return true;

            const list = document.querySelector('ul.ff-list');
            if (!list) return true;

            return false;
        }
        """)

    def wait_vue_stable(self, timeout=5000):
        self.page.wait_for_function(
            """() => {
                const rows = document.querySelectorAll('li.ff-li-list.deparr');
                return rows && rows.length > 0;
            }""",
            timeout=timeout
        )


    def __init__(self, page, loader):
        self.page = page
        self.loader = loader

    def parse_arrivals(self, arrival_airport, current_date, snapshot_flights):


        snapshot_flights = set(snapshot_flights)

        rows = []
        # print(f"   🧠 Parsing {len(snapshot_flights)} flights")

        self.page.keyboard.press("Escape")

        if self.is_vue_unmounted():
            self.wait_vue_stable()

        self.loader.wait_list_stable()

        locator = self.page.locator("li.ff-li-list.deparr")
        total = locator.count()

        # 🔥 snapshot element handles ก่อน
        elements = []

        for i in range(total):
            elements.append(locator.nth(i).element_handle())

        for el in elements:
            try:
                ensure_page_clean(self.page)

                row = self.page.locator("li.ff-li-list.deparr").filter(
                    has=self.page.locator(f"xpath=.", has_text=el.inner_text())
                )

                btn = el.query_selector(".flightsfrom-list-money")
                self.page.evaluate("(e) => e.click()", btn)

                self.page.wait_for_function(
                    "() => document.querySelector('#ff-day-infobox')?.innerText.length > 20",
                    timeout=4000
                )

                popup = self.page.locator("#ff-day-infobox")

                def get_val(label):
                    el2 = popup.locator(
                        f"div.ff-font-s.uk-flex:has(div.ff-font-strong:text-is('{label}')) div.uk-text-right"
                    )
                    return el2.inner_text() if el2.count() else None

                rows.append({
                    "arrival_airport": arrival_airport,
                    "date": current_date,
                    "arrival_time": el.query_selector(".deparr_time div").inner_text(),
                    "flight": el.query_selector(".deparr_flight").inner_text(),
                    "airline": el.query_selector(".deparr_airline_name").inner_text(),
                    "duration": el.query_selector(".deparr_duration").inner_text(),
                    "distance": get_val("Distance"),
                    "aircraft": get_val("Aircraft"),
                    "seats": get_val("Seats"),
                    "codeshare": get_val("Codeshare"),
                    "meals": get_val("Meals"),
                })

                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(120)

            except Exception:
                self.page.keyboard.press("Escape")
                continue

        # 🔎 Debug integrity ก่อน recover
        parsed_set = {r["flight"] for r in rows}
        # print(f"   📊 Snapshot unique flights: {len(snapshot_flights)}")
        print(f"   📊 Parsed unique flights: {len(parsed_set)}")

        rows = self.recover_missing_flights(
            arrival_airport,
            current_date,
            snapshot_flights,
            rows
        )

        return rows


    # ห def parse_arrivals(self, arrival_airport, current_date, snapshot_flights):

    #     rows = []
    #     parsed_set = set()

    #     print(f"   🧠 Parsing {len(snapshot_flights)} flights")

    #     self.loader.wait_list_stable()

    #     for flight_code in snapshot_flights:

    #         try:
    #             ensure_page_clean(self.page)

    #             # 🔥 หา candidate rows ก่อน (substring match ได้)
    #             candidates = self.page.locator(
    #                 "li.ff-li-list.deparr"
    #             ).filter(
    #                 has=self.page.locator(".deparr_flight", has_text=flight_code)
    #             )

    #             if candidates.count() == 0:
    #                 # DOM อาจ refresh
    #                 self.loader.wait_list_stable()
    #                 candidates = self.page.locator(
    #                     "li.ff-li-list.deparr"
    #                 ).filter(
    #                     has=self.page.locator(".deparr_flight", has_text=flight_code)
    #                 )

    #             if candidates.count() == 0:
    #                 print(f"   ⚠️ Flight not found in DOM: {flight_code}")
    #                 continue

    #             # 🔥 กรองให้เหลือ exact match เท่านั้น
    #             row = None
    #             for i in range(candidates.count()):
    #                 candidate = candidates.nth(i)
    #                 text = candidate.locator(".deparr_flight").inner_text().strip()
    #                 if text == flight_code:
    #                     row = candidate
    #                     break

    #             if row is None:
    #                 print(f"   ⚠️ Exact match not found: {flight_code}")
    #                 continue

    #             # 🔥 อ่านข้อมูลจาก row ก่อนเปิด popup
    #             arrival_time = row.locator(".deparr_time div").inner_text()
    #             airline = row.locator(".deparr_airline_name").inner_text()
    #             duration = row.locator(".deparr_duration").inner_text()

    #             btn = row.locator(".flightsfrom-list-money")
    #             btn.click(force=True)

    #             self.page.wait_for_function(
    #                 "() => document.querySelector('#ff-day-infobox')?.innerText.length > 20",
    #                 timeout=5000
    #             )

    #             popup = self.page.locator("#ff-day-infobox")

    #             def get_val(label):
    #                 el = popup.locator(
    #                     f"div.ff-font-s.uk-flex:has(div.ff-font-strong:text-is('{label}')) div.uk-text-right"
    #                 )
    #                 return el.inner_text() if el.count() else None

    #             rows.append({
    #                 "arrival_airport": arrival_airport,
    #                 "date": current_date,
    #                 "arrival_time": arrival_time,
    #                 "flight": flight_code,
    #                 "airline": airline,
    #                 "duration": duration,
    #                 "distance": get_val("Distance"),
    #                 "aircraft": get_val("Aircraft"),
    #                 "seats": get_val("Seats"),
    #                 "codeshare": get_val("Codeshare"),
    #                 "meals": get_val("Meals"),
    #             })

    #             parsed_set.add(flight_code)

    #             self.page.keyboard.press("Escape")
    #             self.loader.wait_list_stable()

    #         except Exception as e:
    #             print(f"   ❌ Failed flight {flight_code} | {e}")
    #             self.page.keyboard.press("Escape")
    #             continue

    #     print(f"   📊 Parsed unique flights: {len(parsed_set)}")

    #     # 🔥 Integrity check
    #     missing = snapshot_flights - parsed_set
    #     if missing:
    #         print(f"   🚨 Missing flights: {len(missing)}")
    #         for m in list(missing)[:5]:
    #             print(f"      - {m}")

    #     return rows
    def recover_missing_flights(
        self,
        arrival_airport,
        current_date,
        snapshot_flights,
        parsed_rows
    ):
        """
        🔥 Recovery pass
        ถ้า snapshot != parsed → ไล่เปิด popup ตาม flight code
        """

        parsed_set = {r["flight"] for r in parsed_rows}
        missing = set(snapshot_flights) - parsed_set

        if not missing:
            return parsed_rows

        print(f"   🔎 Recovery pass → {len(missing)} flights missing")

        self.loader.wait_list_stable()

        for flight_code in missing:

            try:
                ensure_page_clean(self.page)

                # หา row จาก flight code
                candidates = self.page.locator(
                    "li.ff-li-list.deparr"
                ).filter(
                    has=self.page.locator(".deparr_flight", has_text=flight_code)
                )

                if candidates.count() == 0:
                    continue

                row = None
                for i in range(candidates.count()):
                    candidate = candidates.nth(i)
                    text = candidate.locator(".deparr_flight").inner_text().strip()
                    if text == flight_code:
                        row = candidate
                        break

                if row is None:
                    continue

                # อ่านข้อมูลก่อนเปิด popup
                arrival_time = row.locator(".deparr_time div").inner_text()
                airline = row.locator(".deparr_airline_name").inner_text()
                duration = row.locator(".deparr_duration").inner_text()

                btn = row.locator(".flightsfrom-list-money")
                btn.click(force=True)

                self.page.wait_for_function(
                    "() => document.querySelector('#ff-day-infobox')?.innerText.length > 20",
                    timeout=5000
                )

                popup = self.page.locator("#ff-day-infobox")

                def get_val(label):
                    el = popup.locator(
                        f"div.ff-font-s.uk-flex:has(div.ff-font-strong:text-is('{label}')) div.uk-text-right"
                    )
                    return el.inner_text() if el.count() else None

                parsed_rows.append({
                    "arrival_airport": arrival_airport,
                    "date": current_date,
                    "arrival_time": arrival_time,
                    "flight": flight_code,
                    "airline": airline,
                    "duration": duration,
                    "distance": get_val("Distance"),
                    "aircraft": get_val("Aircraft"),
                    "seats": get_val("Seats"),
                    "codeshare": get_val("Codeshare"),
                    "meals": get_val("Meals"),
                })

                self.page.keyboard.press("Escape")
                self.loader.wait_list_stable()

            except Exception:
                self.page.keyboard.press("Escape")
                continue

        print(f"   ✅ After recovery → {len(parsed_rows)} rows")

        return parsed_rows
