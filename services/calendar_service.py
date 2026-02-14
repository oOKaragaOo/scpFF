# class CalendarService:
#     def __init__(self, page):
#         self.page = page

#     # =========================
#     # PRIVATE HELPERS
#     # =========================

#     def _wait_overlay_clear(self):
#         try:
#             self.page.wait_for_selector(
#                 ".pageload-background",
#                 state="detached",
#                 timeout=15000
#             )
#         except:
#             pass

#     def _is_calendar_open(self):
#         return self.page.locator(
#             ".flatpickr-calendar.open"
#         ).count() > 0

#     def _click_open_button(self):
#         try:
#             self.page.evaluate("""
#                 () => {
#                     const btn = document.querySelector("a.select-date");
#                     if (btn) btn.click();
#                 }
#             """)
#         except:
#             pass

#     def _wait_calendar_open(self):
#         self.page.wait_for_selector(
#             ".flatpickr-calendar.open",
#             timeout=10000
#         )
#     # move to loader
#     # def _reset_row_tracker(self):
#     #     try:
#     #         self.page.evaluate("window.__lastCount = undefined;")
#     #     except:
#     #         pass

#     def _set_year(self, year):
#         year_input = self.page.locator(
#             ".flatpickr-calendar.open input.cur-year"
#         )
#         year_input.fill(str(year))
#         year_input.press("Enter")

#     def _set_month(self, month):
#         month_select = self.page.locator(
#             ".flatpickr-calendar.open select.flatpickr-monthDropdown-months"
#         )
#         month_select.select_option(str(month - 1))

#     def _wait_month_change_settle(self):
#         self.page.wait_for_timeout(500)
    
#     def _format_day_label(self, target_date):
#         return target_date.strftime("%B %#d, %Y")  # Windows

#     def _get_day_locator(self, label):
#         return self.page.locator(
#             f".flatpickr-day[aria-label='{label}']"
#         )

#     def _click_day(self, locator):
#         locator.first.click(force=True)

#     # =========================
#     # PUBLIC
#     # =========================

#     def open_calendar(self):

#         # 1️⃣ overlay clear
#         self._wait_overlay_clear()

#         # 2️⃣ ถ้าเปิดอยู่แล้ว → return
#         if self._is_calendar_open():
#             return

#         # 3️⃣ click รอบที่ 1
#         self._click_open_button()
#         self._wait_calendar_open()

#         # 4️⃣ overlay clear อีกครั้ง
#         self._wait_overlay_clear()

#         # 5️⃣ reset row tracker move to loader
#         # self._reset_row_tracker() 

#         # 6️⃣ ถ้าเปิดอยู่แล้ว → return
#         if self._is_calendar_open():
#             return

#         # 7️⃣ click รอบที่ 2
#         self._click_open_button()
#         self._wait_calendar_open()

#         # 8️⃣ ถ้าเปิดอยู่แล้ว → return
#         if self._is_calendar_open():
#             return

#         # 9️⃣ click รอบที่ 3
#         self._click_open_button()
#         self._wait_calendar_open()

#     def goto_month_year(self, year, month):

#         self.open_calendar()

#         self._set_year(year)
#         self._set_month(month)

#         self._wait_month_change_settle()

#         return True

#     def click_calendar_day(self, target_date):

#         label = self._format_day_label(target_date)

#         day_locator = self._get_day_locator(label)

#         self._click_day(day_locator)

from datetime import datetime

class DeterministicCalendarService:
    def __init__(self, page):
        self.page = page

    # =========================
    # PRIVATE HELPERS
    # =========================
    def _click_day(self, locator):
        locator.first.click(force=True)

    def _wait_month_change_settle(self):
        self.page.wait_for_timeout(500)
    
    def _set_month(self, month):
        month_select = self.page.locator(
            ".flatpickr-calendar.open select.flatpickr-monthDropdown-months"
        )
        month_select.select_option(str(month - 1))

    def _set_year(self, year):
        year_input = self.page.locator(
            ".flatpickr-calendar.open input.cur-year"
        )
        year_input.fill(str(year))
        year_input.press("Enter")

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

    def _format_day_label(self, target_date):
        return target_date.strftime("%B %#d, %Y")  # windows flatpickr label

    def _get_day_locator(self, label):
        return self.page.locator(
            f".flatpickr-day[aria-label='{label}']"
        )

    def _is_disabled(self, locator):
        cls = locator.first.get_attribute("class") or ""
        return "disabled" in cls

    def _has_class(self, locator, class_name):
        cls = locator.first.get_attribute("class") or ""
        return class_name in cls

    def _verify_selected(self, label):
        selected = self.page.locator(".flatpickr-day.selected")

        if selected.count() != 1:
            return False

        selected_label = selected.first.get_attribute("aria-label")
        return selected_label == label

    # =========================
    # CALENDAR OPEN
    # =========================

    def open_calendar(self):
        self._wait_overlay_clear()

        if self._is_calendar_open():
            return

        self._click_open_button()
        self._wait_calendar_open()
        self._wait_overlay_clear()

        if self._is_calendar_open():
            return

        self._click_open_button()
        self._wait_calendar_open()

    # =========================
    # MAIN STATE MACHINE
    # =========================
    def goto_month_year(self, year, month):

        self.open_calendar()

        self._set_year(year)
        self._set_month(month)

        self._wait_month_change_settle()

        return True

    # def click_calendar_day(self, target_date):

    #     label = self._format_day_label(target_date)

    #     day_locator = self._get_day_locator(label)

    #     self._click_day(day_locator)

    def resolve_target_date(self, target_date):

        target_label = self._format_day_label(target_date)

        print(f"📅 resolve_target_date → {target_label}")

        # STEP 1 — ensure calendar open
        self.open_calendar()

        # STEP 2 — try current grid
        day = self._get_day_locator(target_label)

        if day.count() > 0:

            day_class = day.first.get_attribute("class") or ""
            print(f"📦 current grid class = {day_class}")

            if not self._is_disabled(day):

                print("✅ normal grid click")
                day.first.click()

                result = self._verify_selected(target_label)
                print(f"🎯 verify selected = {result}")

                return result

            print("⚠️ day disabled → fallback")

        else:
            print("⚠️ day not found → fallback")

        # FALLBACK
        return self._fallback_prev_month(target_label)

    def _fallback_prev_month(self, target_label):

        print("🔥 ENTER FALLBACK MODE")

        prev_btn = self.page.locator(".flatpickr-prev-month")
        next_btn = self.page.locator(".flatpickr-next-month")

        if prev_btn.count() == 0:
            print("❌ prev month button not found")
            return False

        # =========================
        # STEP 1 — move back ONCE
        # =========================
        print("⬅️ click prev month (ONCE)")
        prev_btn.first.click()

        # wait until target day appears in new state
        try:
            self.page.wait_for_selector(
                f".flatpickr-day[aria-label='{target_label}']",
                timeout=3000
            )
        except:
            print("⚠️ month render wait timeout (continue)")

        # re-query AFTER render
        day = self._get_day_locator(target_label)

        # =========================
        # CASE: NOT FOUND
        # =========================
        if day.count() == 0:
            print("❌ target day not found → restore month")

            if next_btn.count() > 0:
                next_btn.first.click()

            return False

        day_class = day.first.get_attribute("class") or ""
        print(f"📦 day class = {day_class}")

        # =========================
        # CASE: DISABLED
        # =========================
        if self._is_disabled(day):
            print("❌ day disabled → restore month")

            if next_btn.count() > 0:
                next_btn.first.click()

            return False

        # =========================
        # CASE: WRONG GRID TYPE
        # =========================
        if "nextMonthDay" not in day_class:
            print("❌ not nextMonthDay → restore month")

            if next_btn.count() > 0:
                next_btn.first.click()

            return False

        # =========================
        # SUCCESS
        # =========================
        print("✅ fallback click")
        day.first.click()

        print("🎯 fallback accepted (skip verify block)")
        return True
