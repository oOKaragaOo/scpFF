class DeterministicCalendarService:

    def __init__(self, page, guard):
        self.page = page
        self.guard = guard
        

# =========================
# PUBLIC
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

    # def goto_month_year(self, year, month):

    #     self.open_calendar()

    #     self._set_year(year)
    #     self._set_month(month)

    #     self._wait_month_change_settle()

    #     return True

    def resolve_target_date(self, target_date):

        self.guard.ensure_page_clean()
        target_label = self._format_day_label(target_date)

        print(f"\ntarget in 📅 : {target_label}")

        # STEP 1 — ensure calendar open
        self.open_calendar()
        self.goto_month_year(target_date.year, target_date.month)
        self._wait_month_stable()
        self._wait_calendar_grid_ready()


        # STEP 2 — try current grid
        day = self._get_day_locator(target_label)

        if day.count() > 0:
            self._wait_day_ready(day)
            day_class = day.first.get_attribute("class") or ""
            # print(f"📦 current grid class = {day_class}")

            if not self._is_disabled(day):

                # print("✅ normal grid click")

                self._wait_calendar_grid_ready()
                self._wait_day_ready(day)
                day.first.click()
                self.page.wait_for_timeout(100)


                result = self._verify_selected(target_label)
                # print(f"🎯 verify selected = {result}")

                return result

            print("⚠️ day disabled → fallback")

        else:
            print("⚠️ day not found → fallback")

        # FALLBACK
        return self._fallback_prev_month(target_label)

    # tqdm def resolve_target_date(self, target_date):

    #     self.guard.ensure_page_clean()
    #     target_label = self._format_day_label(target_date)

    #     # STEP 1 — ensure calendar open
    #     self.open_calendar()
    #     self.goto_month_year(target_date.year, target_date.month)
    #     self._wait_month_stable()
    #     self._wait_calendar_grid_ready()

    #     # STEP 2 — try current grid
    #     day = self._get_day_locator(target_label)

    #     if day.count() > 0:

    #         self._wait_day_ready(day)

    #         if not self._is_disabled(day):

    #             self._wait_calendar_grid_ready()
    #             self._wait_day_ready(day)

    #             day.first.click()
    #             self.page.wait_for_timeout(100)

    #             return self._verify_selected(target_label)

    #     # FALLBACK
    #     return self._fallback_prev_month(target_label)


    def goto_month_year(self, year, month):

        self.open_calendar()

        # target ต้อง fix
        target = (year, month)

        for _ in range(12):  # safety limit

            current_month, current_year = self._read_current_month_year()

            if (current_year, current_month) == target:
                break

            if (current_year, current_month) < target:
                self.page.locator(".flatpickr-next-month").first.click()
            else:
                self.page.locator(".flatpickr-prev-month").first.click()

            self.page.wait_for_timeout(250)

        self._wait_month_stable()

        return True


# =========================
# MAIN STATE
# =========================

    def _fallback_prev_month(self, target_label):

        # print("🔥 ENTER FALLBACK MODE")

        prev_btn = self.page.locator(".flatpickr-prev-month")
        next_btn = self.page.locator(".flatpickr-next-month")

        if prev_btn.count() == 0:
            print("❌ prev month button not found")
            return False

        # print("⬅️ click prev month (ONCE)")
        prev_btn.first.click()

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
            # print("❌ target day not found → restore month")

            if next_btn.count() > 0:
                next_btn.first.click()

            return False

        day_class = day.first.get_attribute("class") or ""
        print(f"📦 day class = {day_class}")

        # =========================
        # CASE: DISABLED
        # =========================
        if self._is_disabled(day):
            # print("❌ day disabled → restore month")

            if next_btn.count() > 0:
                next_btn.first.click()

            return False

        # =========================
        # CASE: WRONG GRID TYPE
        # =========================
        if "nextMonthDay" not in day_class:
            # print("❌ not nextMonthDay → restore month")

            if next_btn.count() > 0:
                next_btn.first.click()

            return False

        # =========================
        # SUCCESS
        # =========================
        print("✅ fallback click")

        self._wait_calendar_grid_ready()
        self._wait_day_ready(day)
        day.first.click()

        # print("🎯 fallback accepted (skip verify block)")
        return True

# =========================
# VALIDATION / HELPERS 
# =========================
    def warmup_calendar(self, start_date):

        print("🔥 Calendar warmup")

        try:
            # กัน popup/overlay ค้าง
            self.guard.ensure_page_clean()

            self.open_calendar()

            # render เดือนแรกของ range
            self.goto_month_year(start_date.year, start_date.month)

            # รอ grid complete
            self._wait_calendar_grid_ready()

            # ให้ interactive state stabilize
            self.page.wait_for_timeout(200)

        finally:
            try:
                self.close_calendar()
            except:
                pass

    def _wait_calendar_grid_ready(self):

        for _ in range(8):   # ~800ms max
            days = self.page.locator(
                ".flatpickr-calendar.open .flatpickr-day"
            ).count()

            # เดือนปกติควรมี ~35-42 cells
            if days >= 35:
                return

            self.page.wait_for_timeout(100)

    def _wait_day_ready(self, day_locator):

        for _ in range(5):   # ~500ms max
            if day_locator.count() == 0:
                break

            cls = day_locator.first.get_attribute("class") or ""

            if "flatpickr-disabled" not in cls:
                return

            self.page.wait_for_timeout(100)

    def _wait_month_stable(self):

        m1 = self._read_current_month_year()
        self.page.wait_for_timeout(150)
        m2 = self._read_current_month_year()

        if m1 != m2:
            self.page.wait_for_timeout(300)

    def _read_current_month_year(self):
        month_select = self.page.locator(
            ".flatpickr-calendar.open select.flatpickr-monthDropdown-months"
        )
        year_input = self.page.locator(
            ".flatpickr-calendar.open input.cur-year"
        )

        month = int(month_select.input_value()) + 1
        year = int(year_input.input_value())

        return month, year

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




