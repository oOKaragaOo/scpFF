import re


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

    def _click_show_more(self):
        button = self.page.locator("#show-more-routes")

        try:
            with self.page.expect_response(
                lambda r: (
                    "entityType=arrivals" in r.url and
                    "take=" in r.url and
                    r.status == 200
                ),
                timeout=30000
            ):
                button.first.click(force=True)

            print("      👉 Clicked show more (XHR detected)")
            return True

        except:
            print("      ❌ Click failed or no XHR")
            return False

    def _wait_dom_settle(self):
        self.page.wait_for_timeout(800)

    # =========================
    # PUBLIC
    # =========================

    def wait_overlay_clear(self):
        try:
            self.page.wait_for_selector(
                ".pageload-background",
                state="detached",
                timeout=15000
            )
        except:
            pass

    def get_expected_rows(self):
        text = self.page.locator("#foundText").inner_text()
        match = re.search(r"Found\s+(\d+)", text)
        return int(match.group(1)) if match else 0

    def wait_list_stable(self):

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

    def ensure_all_rows_loaded(self):

        expected = self.get_expected_rows()
        print("      🎯 Expected rows:", expected)

        while True:

            current = self._get_current_row_count()
            print(f"      📦 Loop | Currently loaded: {current}")

            if self._is_fully_loaded(current, expected):
                print("      ✅ All rows loaded.")
                break

            if not self._has_show_more_button():
                print("      ❌ No more show more button")
                break

            if not self._wait_button_enabled():
                print("      ⚠️ Button not ready")
                break

            if not self._click_show_more():
                break

            self._wait_dom_settle()

        print(
            "      🟢 Final row count:",
            self._get_current_row_count()
        )
