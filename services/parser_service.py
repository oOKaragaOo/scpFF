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

        self.loader.wait_list_stable()

        locator = self.page.locator("li.ff-li-list.deparr")
        total = locator.count()

        # 🔥 snapshot element handles ก่อน
        elements = []

        for i in range(total):
            elements.append(locator.nth(i).element_handle())

        for el in elements:
            try:
                ensure_page_clean(self.page)

                row = self.page.locator("li.ff-li-list.deparr").filter(
                    has=self.page.locator(f"xpath=.", has_text=el.inner_text())
                )

                btn = el.query_selector(".flightsfrom-list-money")
                self.page.evaluate("(e) => e.click()", btn)

                self.page.wait_for_function(
                    "() => document.querySelector('#ff-day-infobox')?.innerText.length > 20",
                    timeout=4000
                )

                popup = self.page.locator("#ff-day-infobox")

                def get_val(label):
                    el2 = popup.locator(
                        f"div.ff-font-s.uk-flex:has(div.ff-font-strong:text-is('{label}')) div.uk-text-right"
                    )
                    return el2.inner_text() if el2.count() else None

                rows.append({
                    "arrival_airport": arrival_airport,
                    "date": current_date,
                    "arrival_time": el.query_selector(".deparr_time div").inner_text(),
                    "flight": el.query_selector(".deparr_flight").inner_text(),
                    "airline": el.query_selector(".deparr_airline_name").inner_text(),
                    "duration": el.query_selector(".deparr_duration").inner_text(),
                    "distance": get_val("Distance"),
                    "aircraft": get_val("Aircraft"),
                    "seats": get_val("Seats"),
                    "codeshare": get_val("Codeshare"),
                    "meals": get_val("Meals"),
                })

                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(120)

            except Exception:
                self.page.keyboard.press("Escape")
                continue

        return rows
