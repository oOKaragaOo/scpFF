class CalendarService:
    def __init__(self, page):
        self.page = page

    # =========================
    # PRIVATE HELPERS
    # =========================

    def _wait_overlay_clear(self):
        try:
            self.page.wait_for_selector(
                ".pageload-background",
                state="detached",
                timeout=15000
            )
        except:
            pass

    def _is_calendar_open(self):
        return self.page.locator(
            ".flatpickr-calendar.open"
        ).count() > 0

    def _click_open_button(self):
        try:
            self.page.evaluate("""
                () => {
                    const btn = document.querySelector("a.select-date");
                    if (btn) btn.click();
                }
            """)
        except:
            pass

    def _wait_calendar_open(self):
        self.page.wait_for_selector(
            ".flatpickr-calendar.open",
            timeout=10000
        )
    # move to loader
    # def _reset_row_tracker(self):
    #     try:
    #         self.page.evaluate("window.__lastCount = undefined;")
    #     except:
    #         pass

    def _set_year(self, year):
        year_input = self.page.locator(
            ".flatpickr-calendar.open input.cur-year"
        )
        year_input.fill(str(year))
        year_input.press("Enter")

    def _set_month(self, month):
        month_select = self.page.locator(
            ".flatpickr-calendar.open select.flatpickr-monthDropdown-months"
        )
        month_select.select_option(str(month - 1))

    def _wait_month_change_settle(self):
        self.page.wait_for_timeout(500)
    
    def _format_day_label(self, target_date):
        return target_date.strftime("%B %#d, %Y")  # Windows

    def _get_day_locator(self, label):
        return self.page.locator(
            f".flatpickr-day[aria-label='{label}']"
        )

    def _click_day(self, locator):
        locator.first.click(force=True)

    # =========================
    # PUBLIC
    # =========================

    def open_calendar(self):

        # 1️⃣ overlay clear
        self._wait_overlay_clear()

        # 2️⃣ ถ้าเปิดอยู่แล้ว → return
        if self._is_calendar_open():
            return

        # 3️⃣ click รอบที่ 1
        self._click_open_button()
        self._wait_calendar_open()

        # 4️⃣ overlay clear อีกครั้ง
        self._wait_overlay_clear()

        # 5️⃣ reset row tracker move to loader
        # self._reset_row_tracker() 

        # 6️⃣ ถ้าเปิดอยู่แล้ว → return
        if self._is_calendar_open():
            return

        # 7️⃣ click รอบที่ 2
        self._click_open_button()
        self._wait_calendar_open()

        # 8️⃣ ถ้าเปิดอยู่แล้ว → return
        if self._is_calendar_open():
            return

        # 9️⃣ click รอบที่ 3
        self._click_open_button()
        self._wait_calendar_open()

    def goto_month_year(self, year, month):

        self.open_calendar()

        self._set_year(year)
        self._set_month(month)

        self._wait_month_change_settle()

        return True

    def click_calendar_day(self, target_date):

        label = self._format_day_label(target_date)

        day_locator = self._get_day_locator(label)

        self._click_day(day_locator)

