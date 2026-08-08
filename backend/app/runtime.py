from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from playwright.async_api import Browser, Playwright, async_playwright

from .planner import Planner
from .schemas import AgentTask, EventKind, RuntimeEvent, TaskStatus


class TaskStore:
    """In-memory task store with per-task event streams.

    Replace this seam with Postgres/Redis before running distributed workers.
    """

    def __init__(self) -> None:
        self.tasks: dict[UUID, AgentTask] = {}
        self.streams: dict[UUID, asyncio.Queue[RuntimeEvent]] = {}

    def create(self, task: AgentTask) -> AgentTask:
        self.tasks[task.id] = task
        self.streams[task.id] = asyncio.Queue()
        return task

    def get(self, task_id: UUID) -> AgentTask | None:
        return self.tasks.get(task_id)

    def list(self) -> list[AgentTask]:
        return sorted(self.tasks.values(), key=lambda task: task.created_at, reverse=True)

    async def emit(self, task: AgentTask, kind: EventKind, message: str, **data: object) -> None:
        event = RuntimeEvent(kind=kind, message=message, data=data)
        task.events.append(event)
        task.updated_at = datetime.utcnow()
        await self.streams[task.id].put(event)

    async def events(self, task_id: UUID) -> AsyncIterator[RuntimeEvent]:
        queue = self.streams[task_id]
        while True:
            yield await queue.get()


class BrowserManager:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def stop(self) -> None:
        browser, playwright = self._browser, self._playwright
        self._browser = None
        self._playwright = None
        # Uvicorn's reload process may already have closed Playwright's
        # transport; teardown must remain safe in that case.
        if browser:
            with suppress(Exception):
                await browser.close()
        if playwright:
            with suppress(Exception):
                await playwright.stop()

    async def observe(self, url: str) -> tuple[str, str]:
        if not self._browser:
            raise RuntimeError("Browser is not available")
        page = await self._browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            title = await page.title()
            return title, page.url
        finally:
            await page.close()


class AgentRuntime:
    def __init__(self, store: TaskStore, browser: BrowserManager, planner: Planner) -> None:
        self.store = store
        self.browser = browser
        self.planner = planner
        self.workers: dict[UUID, asyncio.Task[None]] = {}

    def launch(self, task: AgentTask) -> None:
        self.workers[task.id] = asyncio.create_task(self.run(task))

    async def cancel(self, task: AgentTask) -> None:
        worker = self.workers.get(task.id)
        if worker and not worker.done():
            worker.cancel()
        task.status = TaskStatus.CANCELLED
        await self.store.emit(task, EventKind.SYSTEM, "Task cancelled by operator")

    async def run(self, task: AgentTask) -> None:
        try:
            task.status = TaskStatus.PLANNING
            await self.store.emit(task, EventKind.SYSTEM, "Task accepted by runtime")
            plan = await self.planner.create(task.objective, task.start_url, task.max_steps)
            task.plan = plan.steps
            await self.store.emit(task, EventKind.PLAN, "Execution plan created", steps=task.plan, provider=plan.provider)
            await asyncio.sleep(0.35)

            task.status = TaskStatus.RUNNING
            await self.store.emit(task, EventKind.ACTION, "Browser session allocated", headless=self.browser.headless)
            if task.start_url:
                await self.store.emit(task, EventKind.ACTION, "Navigating to starting URL", url=task.start_url)
                try:
                    title, final_url = await self.browser.observe(task.start_url)
                    await self.store.emit(task, EventKind.OBSERVATION, "Page observed", title=title, url=final_url)
                    task.result = f"Observed {title or 'page'} at {final_url}. Objective ready for model-guided continuation."
                except Exception as exc:
                    task.status = TaskStatus.RECOVERING
                    await self.store.emit(task, EventKind.RECOVERY, "Navigation failed; retaining task context", reason=str(exc))
                    task.result = "The initial page could not be reached. Review the event trail and retry with a reachable URL."
            else:
                await self.store.emit(task, EventKind.OBSERVATION, "No start URL supplied; plan is ready for a model-directed action")
                task.result = "Plan created. Provide a starting URL to begin a browser run."
            task.status = TaskStatus.COMPLETED
            await self.store.emit(task, EventKind.SYSTEM, "Task completed", result=task.result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            await self.store.emit(task, EventKind.ERROR, "Task failed", error=str(exc))
        finally:
            self.workers.pop(task.id, None)
