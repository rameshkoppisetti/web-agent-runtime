from __future__ import annotations

from abc import ABC, abstractmethod
from playwright.async_api import Page


class BrowserTool(ABC):
    """Base interface for reusable browser tools."""

    name: str

    @abstractmethod
    async def run(self, page: Page, **kwargs):
        raise NotImplementedError