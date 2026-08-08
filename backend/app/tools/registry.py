from __future__ import annotations

from playwright.async_api import Page

from .base import BrowserTool


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, BrowserTool] = {}

    def register(self, tool: BrowserTool):
        self.tools[tool.name] = tool

    def list_tools(self) -> list[str]:
        return sorted(self.tools.keys())

    async def execute(self, name: str, page: Page, **kwargs):
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return await self.tools[name].run(page, **kwargs)