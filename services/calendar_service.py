import time
class DeterministicCalendarService:

    def __init__(self, page, guard):
        self.page = page
        self.guard = guard
        

# =========================
# PUBLIC
# =========================


    # def open_calendar(self):

    #     if self._is_calendar_open(debug=True):
    #         print("📅 calendar already open")
    #         return True

    #     print("📅 opening calendar...")

    #     for i in range(3):

    #         self.guard.ensure_page_clean()
    #         self._click_open_button()

    #         for _ in range(20):
    #             if self._is_calendar_open(debug=True):
    #                 print(f"✅ calendar opened (try {i+1})")
    #                 return True

    #             self.page.wait_for_timeout(100)

    #     print("❌ calendar open failed")
    #     return False

    def open_calendar(self):

        # ถ้าเปิดอยู่แล้ว
        if self._is_calendar_open():
            return True

        # -------------------------
        # NORMAL TRY
        # -------------------------
        for _ in range(3):

            self.guard.ensure_page_clean()

            self._click_open_button()

            for _ in range(20):
                if self._is_calendar_open():
                    return True

                self.page.wait_for_timeout(100)

        # -------------------------
        # FALLBACK (NEW)
        # -------------------------
        print("⚠️ calendar open failed -> try tab activation")

        self._force_tab_activation_cycle()

        # retry once after tab switch
        for _ in range(20):
            self._click_open_button()

            if self._is_calendar_open():
                print("✅ calendar opened after tab refresh")
                return True

            self.page.wait_for_timeout(100)

        print("❌ calendar open failed")
        return False


    def goto_month_year(self, year, month):

        target = (year, month)

        # =========================
        # ensure calendar open
        # =========================
        if not self.open_calendar():
            print("⚠️ calendar not open → abort month switch")
            return False

        for _ in range(12):  # safety loop

            # กัน calendar หลุดระหว่างทาง
            if not self._is_calendar_open():
                print("⚠️ calendar closed -> reopen")
                if not self.open_calendar():
                    return False

            # =========================
            # read current month/year
            # =========================
            try:
                current_month, current_year = self._read_current_month_year()
            except Exception as e:
                print("⚠️ read month failed:", e)
                return False

            # target reached
            if (current_year, current_month) == target:
                break

            # =========================
            # choose button (VISIBLE ONLY)
            # =========================
            if (current_year, current_month) < target:
                btn = self.page.locator(
                    ".flatpickr-calendar.open:visible .flatpickr-next-month:visible"
                )
            else:
                btn = self.page.locator(
                    ".flatpickr-calendar.open:visible .flatpickr-prev-month:visible"
                )

            if btn.count() == 0:
                print("❌ month button not visible")
                return False

            # =========================
            # click month
            # =========================
            btn.first.click()

            # ⭐ IMPORTANT FIX
            # ต้อง stable ก่อนถึงไปต่อ
            if not self._wait_single_open_calendar():
                print("⚠️ calendar not stabilized -> abort")
                return False

            self._wait_calendar_grid_ready()

        # =========================
        # final stabilization
        # =========================
        self._wait_month_stable()

        return True


# =========================
# MAIN STATE
# =========================

    def resolve_target_date(self, target_date):

        self.guard.ensure_page_clean()
        target_label = self._format_day_label(target_date)

        print(f"\ntarget in 📅 : {target_label}")

        # reset per day
        self._resolve_used = False

        # -------------------------
        # calendar ready
        # -------------------------
        self.open_calendar()

        self.goto_month_year(
            target_date.year,
            target_date.month
        )

        self._wait_calendar_grid_ready()

        # -------------------------
        # locate day
        # -------------------------
        day = self.page.locator(
            ".flatpickr-calendar.open:visible "
            f".flatpickr-day[aria-label='{target_label}']"
        )

        if day.count() == 0:
            print("⚠️ day not found → skip")
            return False

        cls = day.first.get_attribute("class") or ""

        # =========================
        # NORMAL CLICK
        # =========================
        if "flatpickr-disabled" not in cls:

            self._wait_day_ready(day)
            day.first.click()

            return self._verify_selected(target_label)

        # =========================
        # DISABLED → RESOLVE (สำคัญ)
        # =========================
        print("⚠️ disabled → resolve_day_selection")

        return self.resolve_day_selection(target_label)

    # def resolve_target_date(self, target_date):

    #     self.guard.ensure_page_clean()
    #     target_label = self._format_day_label(target_date)

    #     print(f"\ntarget in 📅 : {target_label}")

    #     # =========================
    #     # RESET (per day)
    #     # =========================
    #     self._fallback_used = False

    #     # =========================
    #     # STEP 1 — ensure calendar open
    #     # =========================
    #     self.open_calendar()



    #     self.goto_month_year(
    #         target_date.year,
    #         target_date.month
    #     )



    #     self._wait_month_stable()
    #     self._wait_calendar_grid_ready()


    #     # =========================
    #     # Debug
    #     # =========================

    #     self._wait_month_stable()
    #     self._wait_calendar_grid_ready()
    #     # self._wait_day_grid_ready

    #     # =========================
    #     # STEP 2 — locate target day
    #     # =========================
    #     day = self.page.locator(
    #         ".flatpickr-calendar.open:visible "
    #         f".flatpickr-day[aria-label='{target_label}']"
    #     )

    #     need_fallback = False

    #     # ---------- NOT FOUND ----------
    #     if day.count() == 0:
    #         print("⚠️ day not found → skip")
    #         return False

    #     # ---------- READ CLASS ----------
    #     cls = day.first.get_attribute("class") or ""

    #     # =========================
    #     # FALLBACK ONLY CASE
    #     # prevMonthDay + disabled
    #     # =========================
    #     if (
    #         "prevMonthDay" in cls and
    #         "flatpickr-disabled" in cls
    #     ):
    #         print("⚠️ prevMonthDay disabled → fallback")
    #         need_fallback = True

    #     # =========================
    #     # NORMAL DISABLED DAY
    #     # (NO FALLBACK)
    #     # =========================
    #     elif "flatpickr-disabled" in cls:
    #         print("⏭️ disabled normal day → skip (no fallback)")
    #         return False

    #     # =========================
    #     # STEP 3 — normal click
    #     # =========================
    #     if not need_fallback:

    #         self._wait_day_ready(day)
    #         self._wait_calendar_grid_ready()
    #         # self._wait_day_grid_ready()
    #         day.first.click()

    #         return self._verify_selected(target_label)

    #     # =========================
    #     # STEP 4 — FALLBACK (ONCE)
    #     # =========================
    #     if self._fallback_used:
    #         print("⚠️ fallback already used → skip day")
    #         return False

    #     self._fallback_used = True

    #     result = self.resolve_day_selection(target_label)

    #     if not result:
    #         print("⚠️ fallback failed → skip day")
    #         return False

    #     return True


    # def resolve_day_selection(self, target_label):

    #     print("\n🟡 FALLBACK START")
    #     print(f"   target label = {target_label}")

    #     self.guard.ensure_page_clean()

    #     # =========================
    #     # snapshot current month
    #     # =========================
    #     old_month, old_year = self._read_current_month_year()

    #     prev_btn = self.page.locator(
    #         ".flatpickr-calendar.open:visible .flatpickr-prev-month"
    #     )

    #     if prev_btn.count() == 0:
    #         print("❌ no prev button")
    #         print("🟡 FALLBACK END (FAIL)\n")
    #         return False

    #     # =========================
    #     # go previous month
    #     # =========================
    #     print("   ⬅️ click prev month")
    #     prev_btn.first.click()

    #     # wait month changed จริง
    #     for _ in range(20):
    #         m, y = self._read_current_month_year()
    #         if (m, y) != (old_month, old_year):
    #             break
    #         self.page.wait_for_timeout(100)

    #     self._wait_single_open_calendar()
    #     self._wait_calendar_grid_ready()

    #     # =========================
    #     # find ONLY nextMonthDay
    #     # =========================
    #     day = self.page.locator(
    #         ".flatpickr-calendar.open:visible "
    #         f".flatpickr-day.nextMonthDay[aria-label='{target_label}']"
    #     )

    #     print(f"   day locator count = {day.count()}")

    #     if day.count() == 0:
    #         print("❌ no nextMonthDay -> SKIP")
    #         print("🟡 FALLBACK END (FAIL)\n")
    #         return False

    #     cls = day.first.get_attribute("class") or ""

    #     if "disabled" in cls:
    #         print("❌ nextMonthDay disabled -> SKIP")
    #         print("🟡 FALLBACK END (FAIL)\n")
    #         return False

    #     # =========================
    #     # SUCCESS
    #     # =========================
    #     print("✅ fallback click nextMonthDay")

    #     self._wait_day_ready(day)
    #     day.first.click()

    #     print("🟢 FALLBACK END (SUCCESS)\n")
    #     return True

    def resolve_day_selection(self, target_label):

        # กัน loop
        if getattr(self, "_resolve_used", False):
            print("⚠️ resolve already used → skip")
            return False

        self._resolve_used = True

        prev_btn = self.page.locator(
            ".flatpickr-calendar.open:visible .flatpickr-prev-month"
        )

        if prev_btn.count() == 0:
            return False

        # -------------------------
        # PHASE 1: probe previous month
        # -------------------------
        prev_btn.first.click()

        # ⭐ FIX: calendar อาจปิดระหว่าง transition
        if not self.ensure_calendar_open():
            print("⚠️ resolve: calendar closed")
            return False

        self._wait_calendar_grid_ready()

        day = self.page.locator(
            ".flatpickr-calendar.open:visible "
            f".flatpickr-day.nextMonthDay[aria-label='{target_label}']"
        )

        if day.count() == 0:
            print("⏭️ resolve reject → skip")
            return False

        cls = day.first.get_attribute("class") or ""

        # disabled จริง
        if "flatpickr-disabled" in cls:
            print("⏭️ resolved disabled → skip")
            return False

        # -------------------------
        # PHASE 2: click
        # -------------------------
        self._wait_day_ready(day)

        day.first.click()

        print("✅ resolve success")
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
            # self.page.wait_for_timeout(200)

        finally:
            try:
                self.close_calendar()
            except:
                pass

    # def _wait_calendar_grid_ready(self):

    #     for _ in range(20):

    #         # ต้องมี open calendar แค่ 1 ตัว
    #         cals = self.page.locator(".flatpickr-calendar.open")

    #         if cals.count() != 1:
    #             self.page.wait_for_timeout(100)
    #             continue

    #         # ใช้เฉพาะ calendar ที่ visible
    #         days = self.page.locator(
    #             ".flatpickr-calendar.open:visible .flatpickr-day"
    #         ).count()

    #         if days >= 35:
    #             return

    #         self.page.wait_for_timeout(100)

    # def _wait_calendar_grid_ready(self):

    #     self.page.wait_for_function(
    #         """
    #         () => {

    #             // -------------------------
    #             // STATE เดิม
    #             // -------------------------
    #             const cal = Array.from(
    #                 document.querySelectorAll('.flatpickr-calendar.open')
    #             ).find(c => c.offsetParent !== null);

    #             if (!cal) return false;             // not visible

    #             // -------------------------
    #             // SIGNAL 1
    #             // inner opacity ready
    #             // -------------------------
    #             const inner = cal.querySelector(
    #                 '.flatpickr-innerContainer'
    #             );

    #             if (!inner) return false;

    #             const opacity = parseFloat(
    #                 window.getComputedStyle(inner).opacity
    #             );

    #             if (opacity < 0.99) return false;

    #             // -------------------------
    #             // SIGNAL 2
    #             // day grid ready
    #             // -------------------------
    #             const days = cal.querySelectorAll(
    #                 '.dayContainer .flatpickr-day'
    #             );

    #             if (days.length < 35) return false;

    #             return true;
    #         }
    #         """,
    #         timeout=3000
    #     )

    def _wait_calendar_grid_ready(self):

        print("🧪 wait_calendar_grid_ready START")

        # ⭐ รอ calendar กลับมาก่อน
        self.page.wait_for_selector(
            ".flatpickr-calendar.open",
            timeout=3000
        )

        self.page.wait_for_function(
            """
            () => {
                const cal = Array.from(
                    document.querySelectorAll('.flatpickr-calendar.open')
                ).find(c => c.offsetParent !== null);

                if (!cal) return false;

                const days = cal.querySelectorAll(
                    '.dayContainer .flatpickr-day'
                );

                return days.length >= 35;
            }
            """,
            timeout=3000
        )

        print("🧪 wait_calendar_grid_ready END")


    def _wait_day_ready(self, day_locator):

        for _ in range(5):   # ~500ms max
            if day_locator.count() == 0:
                break

            cls = day_locator.first.get_attribute("class") or ""

            if "flatpickr-disabled" not in cls:
                return

            # self.page.wait_for_timeout(100)

    def _wait_month_stable(self):

        m1 = self._read_current_month_year()
        self.page.wait_for_timeout(50)
        m2 = self._read_current_month_year()

        if m1 != m2:
            self.page.wait_for_timeout(300)

    def _read_current_month_year(self):

        # =========================
        # ensure calendar open
        # =========================
        cal = self.page.locator(
            ".flatpickr-calendar.open:visible"
        )

        if cal.count() == 0:
            print("⚠️ calendar not open → retry open")

            self.open_calendar()

            # wait reopen
            for _ in range(20):
                cal = self.page.locator(
                    ".flatpickr-calendar.open:visible"
                )
                if cal.count() == 1:
                    break

                self.page.wait_for_timeout(100)

        # still not open
        if cal.count() == 0:
            raise Exception("calendar not open")

        cal = cal.first

        # =========================
        # read month / year
        # =========================
        month_select = cal.locator(
            "select.flatpickr-monthDropdown-months"
        )

        year_input = cal.locator(
            "input.cur-year"
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

    def _is_calendar_open(self, debug=False):

        cal = self.page.locator(
            ".flatpickr-calendar.open:visible"
        )

        if cal.count() != 1:
            return False

        try:
            # ⭐ check interactive readiness
            days = cal.first.locator(
                ".dayContainer .flatpickr-day"
            ).count()

            if days < 35:
                return False

        except:
            return False

        if debug:
            print(f"📅 calendar ready (days={days})")

        return True

    def _click_open_button(self):

        while True:

            # ⭐ ตรวจ + ปิด ad ระหว่างรอ
            self.guard.ensure_page_clean()

            el = self.page.locator("#calendar-date")

            if el.count():
                cls = el.first.get_attribute("class") or ""

                if "flatpickr-input" in cls:
                    break

            self.page.wait_for_timeout(100)

        self.page.locator("a.select-date").first.click()

    def _wait_calendar_open(self):
        self.page.wait_for_selector(
            ".flatpickr-calendar.open",
            timeout=10000
        )

    def _format_day_label(self, target_date):
        return target_date.strftime("%B %#d, %Y")  # windows flatpickr label

    def _get_day_locator(self, label):
        return self.page.locator(
            f".flatpickr-day[aria-label='{label}']:visible"
        )

    def _is_disabled(self, locator):

        if locator.count() == 0:
            # print("🧪 _is_disabled: locator empty")
            return True

        cls = locator.first.get_attribute("class") or ""

        # print(f"🧪 _is_disabled class = '{cls}'")

        result = "disabled" in cls

        # print(f"🧪 _is_disabled result = {result}")

        return result

    def _has_class(self, locator, class_name):
        cls = locator.first.get_attribute("class") or ""
        return class_name in cls

    def _verify_selected(self, label):

        selected = self.page.locator(".flatpickr-day.selected")
        count = selected.count()

        if count == 0:
            return False

        # check all selected (shadow-safe)
        for i in range(count):
            s = selected.nth(i)

            try:
                aria = s.get_attribute("aria-label")

                # match by aria-label only
                if aria == label:
                    return True

            except Exception:
                pass

        return False

    def _wait_single_open_calendar(self, target_label=None):

        for _ in range(30):

            cals = self.page.locator(
                ".flatpickr-calendar.open:visible"
            )

            if cals.count() != 1:
                self.page.wait_for_timeout(100)
                continue

            cal = cals.first

            if target_label:
                day = cal.locator(
                    f".flatpickr-day[aria-label='{target_label}']"
                )
                if day.count() == 0:
                    self.page.wait_for_timeout(100)
                    continue

            return True   # ⭐ SUCCESS

        print("⚠️ calendar not stabilized")
        return False      # ⭐ FAIL จริง

    def ensure_calendar_open(self):

        # ถ้าเปิดอยู่แล้ว
        if self._is_calendar_open():
            return True

        print("⚠️ calendar not open → retry open")

        # ลองเปิดใหม่
        self.open_calendar()

        # รอให้ขึ้นจริง
        for _ in range(20):
            if self._is_calendar_open():
                return True
            self.page.wait_for_timeout(100)

        print("❌ calendar reopen failed")
        return False

    def _cleanup_hidden_calendars(self):

        self.page.evaluate("""
        () => {
            document
            .querySelectorAll('.flatpickr-calendar')
            .forEach(cal => {
                const style = getComputedStyle(cal);

                if (style.display === 'none' ||
                    style.visibility === 'hidden' ||
                    !cal.classList.contains('open')) {
                    cal.remove();
                }
            });
        }
        """)


    def week_has_selectable_day(self, week_days):

        # calendar ready gate
        self._wait_calendar_grid_ready()

        for d in week_days:

            label = self._format_day_label(d)

            day = self.page.locator(
                ".flatpickr-calendar.open:visible "
                f".flatpickr-day[aria-label='{label}']"
            )

            if day.count() == 0:
                continue

            cls = day.first.get_attribute("class") or ""

            # usable day
            if "flatpickr-disabled" not in cls:
                return True

            # recheck once
            self._wait_calendar_grid_ready()

            cls2 = day.first.get_attribute("class") or ""

            if "flatpickr-disabled" not in cls2:
                return True

        return False


    def _fallback_phase1_probe(self, target_label):

        old_month, old_year = self._read_current_month_year()

        prev_btn = self.page.locator(
            ".flatpickr-calendar.open:visible .flatpickr-prev-month"
        )

        if prev_btn.count() == 0:
            return None

        prev_btn.first.click()

        self._wait_calendar_grid_ready()

        day = self.page.locator(
            ".flatpickr-calendar.open:visible "
            f".flatpickr-day.nextMonthDay[aria-label='{target_label}']"
        )

        if day.count() == 0:
            return None

        cls = day.first.get_attribute("class") or ""

        # ต้องเป็น nextMonthDay เท่านั้น
        if "nextMonthDay" not in cls:
            return None

        return day

    def _fallback_phase2_click(self, day):

        self._wait_calendar_grid_ready()
        self._wait_day_ready(day)

        cls = day.first.get_attribute("class") or ""

        if "flatpickr-disabled" in cls:
            print("❌ phase2 disabled → skip")
            return False

        print("✅ fallback phase2 click")
        day.first.click()

        return True

    def _force_tab_activation_cycle(self):
        """
        fallback only when calendar open failed
        """

        try:
            print("🔄 force tab activation (fallback)")

            dep = self.page.locator(
                "div.shortcut-button:has(a:has-text('Departures'))"
            )
            arr = self.page.locator(
                "div.shortcut-button:has(a:has-text('Arrivals'))"
            )

            dep.first.click()
            self.page.wait_for_timeout(200)

            arr.first.click()
            self.page.wait_for_timeout(200)

        except Exception:
            print("⚠️ tab activation failed")
