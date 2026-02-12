class CalendarService:

    def __init__(self, page):
        self.page = page

    # def open_calendar(self):

    #     # ถ้าเปิดอยู่แล้ว ไม่ต้องกด
    #     if self.page.locator(".flatpickr-calendar.open").count() > 0:
    #         return

    #     try:
    #         self.page.evaluate("""
    #             () => {
    #                 const btn = document.querySelector("a.select-date");
    #                 if (btn) btn.click();
    #             }
    #         """)
    #     except:
    #         pass

    #     self.page.wait_for_selector(
    #         ".flatpickr-calendar.open",
    #         timeout=10000
    #     )

    def goto_month_year(self, year, month):
        self.open_calendar()

        year_input = self.page.locator(
            ".flatpickr-calendar.open input.cur-year"
        )
        year_input.fill(str(year))
        year_input.press("Enter")

        month_select = self.page.locator(
            ".flatpickr-calendar.open select.flatpickr-monthDropdown-months"
        )
        month_select.select_option(str(month - 1))

        self.page.wait_for_timeout(500)
        return True

    def click_calendar_day(self, target_date):
        label = target_date.strftime("%B %#d, %Y")  # Windows

        day_el = self.page.locator(
            f".flatpickr-day[aria-label='{label}']"
        )

        day_el.first.click(force=True)

    # def open_calendar(self):

    #     # ✅ รอ overlay หายก่อนทุกครั้ง
    #     try:
    #         self.page.wait_for_selector(
    #             ".pageload-background",
    #             state="detached",
    #             timeout=15000
    #         )
    #     except:
    #         pass

    def open_calendar(self):

        # ✅ รอ overlay หายก่อน
        try:
            self.page.wait_for_selector(
                ".pageload-background",
                state="detached",
                timeout=15000
            )
        except:
            pass

        # ✅ reset row tracker ทุกครั้งก่อนเปลี่ยนวัน
        # try:
        #     self.page.evaluate("window.__lastCount = undefined;")
        #     print("window")
        # except:
        #     print("cant reset")
        #     pass

        # ถ้าเปิดอยู่แล้ว ไม่ต้องกด
        if self.page.locator(".flatpickr-calendar.open").count() > 0:
            return

        try:
            self.page.evaluate("""
                () => {
                    const btn = document.querySelector("a.select-date");
                    if (btn) btn.click();
                }
            """)
        except:
            pass

        self.page.wait_for_selector(
            ".flatpickr-calendar.open",
            timeout=10000
        )


        # ✅ รอ overlay หายก่อน
        try:
            self.page.wait_for_selector(
                ".pageload-background",
                state="detached",
                timeout=15000
            )
        except:
            pass

        # ✅ reset row tracker ทุกครั้งก่อนเปลี่ยนวัน
        try:
            self.page.evaluate("window.__lastCount = undefined;")
        except:
            print("window.__lastCount XX")
            pass

        # ถ้าเปิดอยู่แล้ว ไม่ต้องกด
        if self.page.locator(".flatpickr-calendar.open").count() > 0:
            return

        try:
            self.page.evaluate("""
                () => {
                    const btn = document.querySelector("a.select-date");
                    if (btn) btn.click();
                }
            """)
        except:
            pass

        self.page.wait_for_selector(
            ".flatpickr-calendar.open",
            timeout=10000
        )

        # ถ้าเปิดอยู่แล้ว ไม่ต้องกด
        if self.page.locator(".flatpickr-calendar.open").count() > 0:
            return

        try:
            self.page.evaluate("""
                () => {
                    const btn = document.querySelector("a.select-date");
                    if (btn) btn.click();
                }
            """)
        except:
            pass

        self.page.wait_for_selector(
            ".flatpickr-calendar.open",
            timeout=10000
        )

