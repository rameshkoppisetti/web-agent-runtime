from __future__ import annotations

from playwright.async_api import Page

from .base import BrowserTool


class ExtractPageTool(BrowserTool):
    name = "extract_page"

    async def run(self, page: Page):
        return {
            "title": await page.title(),
            "url": page.url,
            "text": await page.locator("body").inner_text(),
        }


class ExtractLinksTool(BrowserTool):
    name = "extract_links"

    async def run(self, page: Page):
        links = await page.locator("a").evaluate_all(
            """
            els => els.map(a => ({
                text: a.innerText,
                href: a.href
            }))
            """
        )
        return {"links": links}