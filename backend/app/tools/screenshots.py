from __future__ import annotations

from pathlib import Path

from playwright.async_api import Page

from .base import BrowserTool


class ScreenshotTool(BrowserTool):
    name = "screenshot"

    async def run(self, page: Page, path: str, full_page: bool = True):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        await page.screenshot(path=str(target), full_page=full_page)

        return {
            "path": str(target),
            "full_page": full_page,
        }