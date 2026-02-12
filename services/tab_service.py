class TabService:

    def __init__(self, page):
        self.page = page

    def switch(self, mode: str):

        mode = mode.lower()
        label = mode.capitalize()

        locator = self.page.locator(".shortcut-button a", has_text=label)
        locator.click()

        self.page.wait_for_load_state("networkidle")
