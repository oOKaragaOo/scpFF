from datetime import timedelta
from services.calendar_service import CalendarService
from services.loader_service import LoaderService
from services.parser_service import ParserService
from utils.exporter import export_day_debug

class AirportScraper:

    def __init__(self, page):
        self.page = page
        self.calendar = CalendarService(page)
        self.loader = LoaderService(page)
        self.parser = ParserService(page, self.loader)



    def scrape_airport(self, code, start_date, end_date):

        self.page.goto(
            f"https://www.flightsfrom.com/{code}"
            f"?from={code}&entityType=arrivals&take=100"
            "&dateMethod=month&sorting=arrival-time"
            "&sortingDirection=asc&state=1",
            timeout=60000
        )

        all_rows = []
        current_month = start_date.replace(day=1)

        while current_month <= end_date:

            print(f"\n🗓 Processing month: {current_month.strftime('%Y-%m')}")

            month_rows = self.scrape_current_month(
                code, current_month, start_date, end_date
            )

            all_rows.extend(month_rows)

            next_month = current_month + timedelta(days=32)
            current_month = next_month.replace(day=1)

        print(f"\n✅ DONE | TOTAL ROWS: {len(all_rows)}")
        return all_rows


    def scrape_current_month(self, code, current_month, start_date, end_date):

        from datetime import date
        import time

        year = current_month.year
        month = current_month.month

        month_rows = []

        print(f"\n🗓 Processing month: {current_month.strftime('%Y-%m')}")
        # 🔥 reset state ก่อนเปิด calendar
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)
        
        self.calendar.open_calendar()
        print("   📂 Calendar opened")

        self.calendar.goto_month_year(year, month)
        print(f"   📆 Switched to {year}-{month:02d}")

        for day in range(1, 32):

            try:
                page_date = date(year, month, day)
            except:
                break

            if page_date < start_date or page_date > end_date:
                continue

            print(f"\n📅 {page_date}")

            # 🔥 เปิด calendar ใหม่ทุกวัน (เหมือนที่แก้ล่าสุด)
            self.calendar.open_calendar()

            print("   👉 Clicking calendar day...")
            self.calendar.click_calendar_day(page_date)

            print("   ⏳ Waiting overlay...")
            self.loader.wait_overlay_clear()
            print("   ✅ Overlay cleared")

            self.page.wait_for_timeout(800)

            before_rows = self.page.locator(
                "li.ff-li-list.deparr"
            ).count()
            print(f"   📦 Rows after day click: {before_rows}")

            print("   🚀 Enter ensure_all_rows_loaded")
            self.loader.ensure_all_rows_loaded()
            print("   🏁 Exit ensure_all_rows_loaded")

            print("   🔄 Waiting list stable...")
            self.loader.wait_list_stable()
            print("   ✅ List stable")

            after_rows = self.page.locator(
                "li.ff-li-list.deparr"
            ).count()
            print(f"   📊 Rows before parse: {after_rows}")

            print("   🔍 Start parse_arrivals")
            day_rows = self.parser.parse_arrivals(
                code, page_date.isoformat()
            )
            print("   ✅ parse_arrivals finished")

            scraped = len(day_rows)
            month_rows.extend(day_rows)

            print(f"   📌 Parsed rows: {scraped}")

            export_day_debug(
                day_rows,
                code,
                page_date.isoformat(),
                "arrivals"
            )

            time.sleep(1.2)

        return month_rows
