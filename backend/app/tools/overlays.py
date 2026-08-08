from __future__ import annotations

from playwright.async_api import Page

from .base import BrowserTool


class DismissOverlaysTool(BrowserTool):
    name = "dismiss_overlays"

    async def run(self, page: Page):
        selectors = [
            "button[aria-label='Close']",
            "button:has-text('Close')",
            "button:has-text('Dismiss')",
            "button:has-text('Skip')",
            "button:has-text('Later')",
            "button:has-text('No Thanks')",
            "[data-testid='close']",
            ".close",
            ".modal-close",
            ".overlay-close",
        ]

        dismissed = []

        for selector in selectors:
            locator = page.locator(selector)

            if await locator.count() == 0:
                continue

            try:
                await locator.first.click(timeout=1_000)
                dismissed.append(selector)
            except Exception:
                continue

        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass

        return {"dismissed": dismissed}