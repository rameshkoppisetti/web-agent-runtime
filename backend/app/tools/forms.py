from __future__ import annotations

from playwright.async_api import Page

from .base import BrowserTool


class FillTool(BrowserTool):
    name = "fill"

    async def run(self, page: Page, selector: str, text: str):
        await page.locator(selector).fill(text)
        return {
            "selector": selector,
            "length": len(text),
            "status": "filled",
        }


class SelectOptionTool(BrowserTool):
    name = "select_option"

    async def run(self, page: Page, selector: str, value: str):
        await page.locator(selector).select_option(value)
        return {
            "selector": selector,
            "value": value,
            "status": "selected",
        }