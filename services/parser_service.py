# =========================
# BLOCK ADS / IFRAME
# =========================
def kill_overlays(page):
    page.evaluate("""
    () => {
        const selectors = [
            '#ff-idle-ad',
            '.ff-phone-ad',
            '.phone-ad-show-switch',
            '.ad-container-close',
            '.uk-modal',
            '.uk-overlay',
            '.uk-position-fixed',
            '.ff-footer',
            '.ff-sticky',
            'iframe[src*="ads"]',
            'iframe[src*="doubleclick"]'
        ];

        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });

        // unlock scroll / pointer
        document.body.style.overflow = 'auto';
        document.body.style.pointerEvents = 'auto';

        // footer killer (ตัวปิด content)
        document.querySelectorAll('footer').forEach(f => f.remove());
    }
    """)

def unlock_page(page):
    page.evaluate("""
    () => {
        document.documentElement.style.overflow = 'auto';
        document.body.style.overflow = 'auto';
        document.body.classList.remove('uk-modal-page');
    }
    """)
def overlay_detected(page):
    return page.evaluate("""
    () => !!(
        document.querySelector('#ff-idle-ad') ||
        document.querySelector('.ff-footer') ||
        document.body.style.overflow === 'hidden'
    )
    """)

def ensure_page_clean(page):
    if  overlay_detected(page):
        kill_overlays(page)
        unlock_page(page)

def block_ads(route):
    url = route.request.url
    if any(x in url for x in [
        "doubleclick", "googlesyndication", "adservice",
        "adsystem", "taboola", "outbrain", "facebook"
    ]):
        route.abort()
    else:
        route.continue_()

def close_idle_ad(page):
    try:
        ad = page.locator("#ff-idle-ad")
        if ad.count() > 0 and ad.is_visible():
            close_btn = ad.locator(".ad-container-close")
            if close_btn.count() > 0:
                close_btn.click(force=True)
                page.wait_for_timeout(300)
    except:
        pass

class ParserService:

    def __init__(self, page, loader):
        self.page = page
        self.loader = loader

    def parse_arrivals(self, arrival_airport, current_date):
        rows = []
        failed_indexes = []

        # 🔥 เรียกผ่าน loader
        self.loader.wait_list_stable()

        total = self.page.locator("li.ff-li-list.deparr").count()

        for i in range(total):
            try:
                ensure_page_clean(self.page)  # ถ้ายังเป็น global ก็ปล่อยไว้ก่อน

                row = self.page.locator("li.ff-li-list.deparr").nth(i)
                btn = row.locator(".flightsfrom-list-money")

                self.page.evaluate(
                    "(el) => el.click()",
                    btn.element_handle()
                )

                self.page.wait_for_function(
                    "() => document.querySelector('#ff-day-infobox')?.innerText.length > 20",
                    timeout=4000
                )

                popup = self.page.locator("#ff-day-infobox")

                def get_val(label):
                    el = popup.locator(
                        f"div.ff-font-s.uk-flex:has(div.ff-font-strong:text-is('{label}')) div.uk-text-right"
                    )
                    return el.inner_text() if el.count() else None

                rows.append({
                    "arrival_airport": arrival_airport,
                    "date": current_date,
                    "arrival_time": row.locator(".deparr_time div").inner_text(),
                    "flight": row.locator(".deparr_flight").inner_text(),
                    "airline": row.locator(".deparr_airline_name").inner_text(),
                    "duration": row.locator(".deparr_duration").inner_text(),
                    "distance": get_val("Distance"),
                    "aircraft": get_val("Aircraft"),
                    "seats": get_val("Seats"),
                    "codeshare": get_val("Codeshare"),
                    "meals": get_val("Meals"),
                })

                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(120)

            except Exception:
                failed_indexes.append(i)
                self.page.keyboard.press("Escape")
                continue

        return rows
