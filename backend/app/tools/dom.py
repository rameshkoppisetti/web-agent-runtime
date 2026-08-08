from __future__ import annotations

from playwright.async_api import Page

from .base import BrowserTool


class ClickTool(BrowserTool):
    name = "click"

    async def run(self, page: Page, selector: str):
        await page.locator(selector).click()
        return {"selector": selector, "status": "clicked"}


class WaitForSelectorTool(BrowserTool):
    name = "wait_for_selector"

    async def run(self, page: Page, selector: str, timeout: int = 10_000):
        await page.locator(selector).wait_for(timeout=timeout)
        return {"selector": selector, "status": "visible"}


class GetTextTool(BrowserTool):
    name = "get_text"

    async def run(self, page: Page, selector: str):
        text = await page.locator(selector).inner_text()
        return {"selector": selector, "text": text}