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

            try:
                button.first.click(force=True)
                print("      👉 Clicked show more")
            except:
                print("      ❌ Click failed")
                break

            try:
                self.page.wait_for_function(
                    """(prev) => {
                        return document.querySelectorAll(
                            "li.ff-li-list.deparr"
                        ).length > prev;
                    }""",
                    arg=current,
                    timeout=15000
                )
            except:
                print("      ⚠️ Rows did not increase (timeout)")
                break

        print(
            "      🟢 Final row count:",
            self.page.locator(
                "li.ff-li-list.deparr"
            ).count()
        )

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
