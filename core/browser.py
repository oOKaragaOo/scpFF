from playwright.sync_api import sync_playwright

class BrowserManager:

    def __init__(self):
        self.playwright = None
        self.ctx = None
        self.page = None

    def start(self):
        self.playwright = sync_playwright().start()
        self.ctx = self.playwright.chromium.launch_persistent_context(
            "profile",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.page = self.ctx.new_page()
        return self.page

    def close(self):
        self.ctx.close()
        self.playwright.stop()
