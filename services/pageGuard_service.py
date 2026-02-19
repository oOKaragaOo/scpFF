class PageGuardService:

    def __init__(self, page):
        self.page = page

    # =========================
    # PRIVATE
    # =========================

    def _kill_overlays(self):
        self.page.evaluate("""
        () => {

            const idleOverlay = document.getElementById('ff-idle-overlay');
            if (idleOverlay && idleOverlay.style.display === 'block') {
                if (typeof closeInactivityAd === 'function') {
                    closeInactivityAd();
                } else {
                    idleOverlay.style.display = 'none';
                }
            }

            const idleAd = document.getElementById('ff-idle-ad');
            if (idleAd) {

                const closeBtn = idleAd.querySelector('.ad-container-close');
                if (closeBtn) closeBtn.click();

                // ⭐ force hide กันค้าง
                idleAd.style.display = 'none';
                idleAd.remove();
            }

            const adSelectors = [
                '.ff-phone-ad',
                '.phone-ad-show-switch',
                'iframe[src*="doubleclick"]',
                'iframe[src*="googlesyndication"]',
                'iframe[src*="adservice"]',
                'iframe[src*="adsystem"]',
                'iframe[src*="taboola"]',
                'iframe[src*="outbrain"]',
                'iframe[src*="facebook"]'
            ];

            adSelectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });

            document.documentElement.style.overflow = '';
            document.body.style.overflow = '';
            document.body.style.pointerEvents = '';
            document.body.classList.remove('uk-modal-page');
        }
        """)
    
    def _unlock_page(self):
        self.page.evaluate("""
        () => {
            document.documentElement.style.overflow = 'auto';
            document.body.style.overflow = 'auto';
            document.body.classList.remove('uk-modal-page');
        }
        """)

    def _overlay_detected(self):
        return self.page.evaluate("""
        () => {
            const ad = document.querySelector('#ff-idle-ad');
            const adVisible =
                ad && getComputedStyle(ad).display !== 'none';

            return !!(
                adVisible ||
                document.body.style.overflow === 'hidden'
            );
        }
        """)


    def block_ads(self, route):
        url = route.request.url
        if any(x in url for x in [
            "doubleclick", "googlesyndication", "adservice",
            "adsystem", "taboola", "outbrain", "facebook"
        ]):
            route.abort()
        else:
            route.continue_()

    def close_idle_ad(self):
        try:
            ad = self.page.locator("#ff-idle-ad")
            if ad.count() > 0 and ad.is_visible():
                close_btn = ad.locator(".ad-container-close")
                if close_btn.count() > 0:
                    close_btn.click(force=True)
                    self.page.wait_for_timeout(300)
        except:
            pass

    # =========================
    # VUE GUARD
    # =========================

    def is_vue_unmounted(self):
        return self.page.evaluate("""
        () => {
            const rows = document.querySelectorAll('li.ff-li-list.deparr');
            if (!rows || rows.length === 0) return true;

            const list = document.querySelector('ul.ff-list');
            if (!list) return true;

            return false;
        }
        """)

    def wait_vue_stable(self, timeout=5000):

        print("      🧩 wait_vue_stable: waiting rows OR empty")

        try:
            self.page.wait_for_function(
                """
                () => {
                    const rows = document.querySelectorAll(
                        'li.ff-li-list.deparr'
                    ).length;

                    const empty = document.body.innerText.includes(
                        "did not find any"
                    );

                    return rows > 0 || empty;
                }
                """,
                timeout=timeout
            )

            # debug state หลัง wait ผ่าน
            row_count = self.page.evaluate(
                "document.querySelectorAll('li.ff-li-list.deparr').length"
            )

            empty_flag = self.page.evaluate(
                "document.body.innerText.includes('did not find any')"
            )

            print(f"      ✅ vue stable | rows={row_count} | empty={empty_flag}")

        except Exception as e:
            print("      ❌ wait_vue_stable timeout")
            raise e

    def ensure_vue_ready(self, loader):
        self.page.keyboard.press("Escape")

        if self.is_vue_unmounted():
            self.wait_vue_stable()

        loader.wait_list_stable()

    # =========================
    # PUBLIC
    # =========================

    def ensure_page_clean(self):
        if self._overlay_detected():
            self._kill_overlays()
            self._unlock_page()

