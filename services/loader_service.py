import re
from tqdm import tqdm
import os


class LoaderService:

    def __init__(self, page):
        self.page = page


    # =========================
    # PRIVATE HELPERS
    # =========================

    def _reset_row_tracker(self):
        try:
            self.page.evaluate("""
                window.__lastCount = undefined;
                window.__rowTracker = undefined;
            """)
        except:
            pass

    def _get_current_row_count(self):
        return self.page.locator(
            "li.ff-li-list.deparr"
        ).count()

    def _is_fully_loaded(self, current, expected):
        return current >= expected

    def _has_show_more_button(self):
        return self.page.locator(
            "#show-more-routes"
        ).count() > 0

    def _wait_button_enabled(self):
        try:
            self.page.wait_for_function(
                """() => {
                    const btn = document.querySelector('#show-more-routes');
                    if (!btn) return false;
                    return !btn.disabled;
                }""",
                timeout=15000
            )
            return True
        except:
            return False


    # =========================
    # FIXED SHOW MORE CLICK
    # =========================

    def _click_show_more(self):

        import time

        buttons = self.page.locator("#show-more-routes")
        count = buttons.count()

        # print(f"      🔎 show-more buttons found = {count}")

        target = None

        for i in range(count):
            btn = buttons.nth(i)
            visible = btn.is_visible()
            enabled = btn.is_enabled()

            # print(f"      ▶ btn[{i}] visible={visible} enabled={enabled}")

            if visible and enabled:
                target = btn
                break

        if not target:
            print("      ❌ No usable show more button")
            return False

        before = self._get_current_row_count()
        # print(f"      📊 before_rows = {before}")

        try:
            start = time.time()

            target.click(force=True)
            # print("      🖱 clicked")

            # =========================
            # Reactive growth wait
            # =========================
            self.page.wait_for_function(
                """
                (prev) => {
                    return document.querySelectorAll(
                        "li.ff-li-list.deparr"
                    ).length > prev;
                }
                """,
                arg=before,
                timeout=5000
            )

            # after = self._get_current_row_count()
            # delta = round(time.time() - start, 3)

            # print(f"      ⏱ growth detected in {delta}s | rows={after}")

            return True

        except Exception as e:
            print(f"      ⚠️ no growth within timeout | {e}")
            self.ensure_all_rows_loaded()
            return False

    def _wait_dom_settle(self):
        self.page.wait_for_timeout(800)


    # =========================
    # PUBLIC
    # =========================

    def wait_overlay_clear(self):

        # import time
        # t0 = time.perf_counter()

        try:
            self.page.wait_for_selector(
                ".pageload-background",
                state="detached",
                timeout=5000
            )
        except:
            pass

        # dt = time.perf_counter() - t0
        # print(f"      ⏱ overlay wait: {dt:.2f}s")

        return True

    def get_expected_rows(self):
        text = self.page.locator("#foundText").inner_text()
        match = re.search(r"Found\s+(\d+)", text)
        count = int(match.group(1)) if match else 0

        lower = (text or "").lower()
        if 'departure' in lower or 'departures' in lower:
            scope = 'departures'
        elif 'arrival' in lower or 'arrivals' in lower:
            scope = 'arrivals'
        elif 'flight' in lower or 'flights' in lower:
            scope = 'flights'
        else:
            scope = 'unknown'

        return {"count": count, "scope": scope, "raw": text}

    def wait_list_stable(self):

        # ⭐ ถ้า empty result → ไม่ต้องรอ row
        if self._is_empty_result():
            print("      🟢 wait_list_stable skipped (empty)")
            return True        

        self.page.wait_for_selector(
            "li.ff-li-list.deparr"
        )

        self.page.wait_for_function(
            """() => {
                const rows = document.querySelectorAll(
                    "li.ff-li-list.deparr"
                );
                if (!rows.length) return false;

                const count = rows.length;

                if (!window.__rowTracker) {
                    window.__rowTracker = { last: count, same: 0 };
                    return false;
                }

                if (window.__rowTracker.last === count) {
                    window.__rowTracker.same += 1;
                } else {
                    window.__rowTracker.last = count;
                    window.__rowTracker.same = 0;
                }

                return window.__rowTracker.same >= 2;
            }"""
        )

    def ensure_all_rows_loaded(self, guard=None):

        expected_info = self.get_expected_rows()

        # support older return (int) or new dict {count, scope}
        if isinstance(expected_info, dict):
            expected = int(expected_info.get("count", 0))
        else:
            expected = int(expected_info or 0)

        if self._is_empty_result() or expected == 0:
            return

        try:
            self.wait_overlay_clear()
        except:
            pass

        click_count = 0
        max_click = 50          # safety hard limit
        stagnant_round = 0
        last_count = -1

        with tqdm(
            total=expected,
            desc="Loading flight",
            ascii=("_", "▄"),
            unit="row",
            colour="#26bdeb",
            ncols=140,
            disable=(os.getenv("SCRAPER_DISABLE_TQDM", "0") == "1")
        ) as pbar:

            if guard:
                guard.ensure_page_clean()

            while True:

                current = self._get_current_row_count()

                pbar.n = current
                pbar.set_postfix({"click": click_count})
                pbar.refresh()

                # ✅ fully loaded
                if self._is_fully_loaded(current, expected):
                    break

                # ✅ no more button
                if not self._has_show_more_button():
                    break

                # ✅ stagnant detection
                if current == last_count:
                    stagnant_round += 1
                else:
                    stagnant_round = 0

                if stagnant_round >= 9:
                    print("      ⚠️ row count stagnant — break")
                    break

                last_count = current

                # ✅ max click guard
                if click_count >= max_click:
                    print("      ⚠️ max click reached — break")
                    break

                if not self._wait_button_enabled():
                    break

                if not self._click_show_more():
                    break

                click_count += 1

                self._wait_dom_settle()

                if guard:
                    guard.ensure_page_clean()

    def wait_overlay_then_rows(self):

        # STEP 1 — wait overlay disappear
        self.wait_overlay_clear()

        # STEP 2 — check EMPTY SIGNAL ก่อน
        empty_msg = self.page.locator(
            "div:has-text('Your search did not find any')"
        )

        if empty_msg.count() > 0:
            print("      🟢 empty result detected (no flights)")
            return True

        # STEP 3 — รอ rows แบบ reactive
        try:
            self.page.wait_for_function(
                """
                () => {
                    return document.querySelectorAll(
                        "li.ff-li-list.deparr"
                    ).length > 0;
                }
                """,
                timeout=5000
            )
            return True

        except:
            print("      ⚠️ overlay gone but no rows and no empty message")
            return False

    def _is_empty_result(self):

        try:
            return self.page.evaluate("""
            () => {
                const text = document.body.innerText || "";
                const emptyDeparture =
                    text.includes("did not find any departures");
                const emptyArrival =
                    text.includes("did not find any arrivals");

                const rows =
                    document.querySelectorAll(
                        "li.ff-li-list.deparr"
                    ).length;

                return (emptyDeparture || emptyArrival) && rows === 0;
            }
            """)
        except:
            return False

    def _debug_empty_result(self):
        locator = self.page.locator("text=Your search did not find")

        count = locator.count()
        visible = False

        if count > 0:
            try:
                visible = locator.first.is_visible()
            except:
                pass

        print(f"      🔎 EMPTY DEBUG → count={count} | visible={visible}")
        html = self.page.content()
        print("EMPTY TEXT FOUND?" , "Your search did not find" in html)
        
