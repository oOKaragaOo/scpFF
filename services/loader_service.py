import re

class LoaderService:

    def __init__(self, page):
        self.page = page

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
                if (window.__lastCount === count) return true;
                window.__lastCount = count;
                return false;
            }"""
        )

    def ensure_all_rows_loaded(self):

        expected = self.get_expected_rows()
        print("      🎯 Expected rows:", expected)

        while True:

            current = self.page.locator(
                "li.ff-li-list.deparr"
            ).count()

            print(f"      📦 Loop | Currently loaded: {current}")

            if current >= expected:
                print("      ✅ All rows loaded.")
                break

            button = self.page.locator("#show-more-routes")

            if button.count() == 0:
                print("      ❌ No more show more button")
                break

            # รอปุ่ม enable ก่อน
            try:
                self.page.wait_for_function(
                    """() => {
                        const btn = document.querySelector('#show-more-routes');
                        if (!btn) return false;
                        return !btn.disabled;
                    }""",
                    timeout=15000
                )
            except:
                print("      ⚠️ Button not ready")
                break

            # click แล้วรอ XHR arrivals ยิงจริง
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

            except:
                print("      ❌ Click failed or no XHR")
                break

            # รอ Vue render สั้น ๆ ให้ DOM เสถียร
            self.page.wait_for_timeout(800)

        print(
            "      🟢 Final row count:",
            self.page.locator(
                "li.ff-li-list.deparr"
            ).count()
        )

    # def wait_list_stable(self):

    #     self.page.wait_for_selector(
    #         "li.ff-li-list.deparr"
    #     )

    #     self.page.wait_for_function(
    #         """() => {
    #             const rows = document.querySelectorAll(
    #                 "li.ff-li-list.deparr"
    #             );
    #             if (!rows.length) return false;

    #             const count = rows.length;

    #             if (!window.__rowTracker) {
    #                 window.__rowTracker = { last: count, same: 0 };
    #                 return false;
    #             }

    #             if (window.__rowTracker.last === count) {
    #                 window.__rowTracker.same += 1;
    #             } else {
    #                 window.__rowTracker.last = count;
    #                 window.__rowTracker.same = 0;
    #             }

    #             return window.__rowTracker.same >= 2;
    #         }"""
    #     )
