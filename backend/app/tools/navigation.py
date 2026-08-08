from __future__ import annotations

from playwright.async_api import Page

from .base import BrowserTool


class NavigateTool(BrowserTool):
    name = "navigate"

    async def run(
        self,
        page: Page,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 20_000,
    ):
        await page.goto(url, wait_until=wait_until, timeout=timeout)
        return {
            "url": page.url,
            "title": await page.title(),
        }