from __future__ import annotations

import asyncio
import re
from contextlib import suppress
from datetime import date
from datetime import datetime
from typing import AsyncIterator, TypedDict
from uuid import UUID
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from playwright.async_api import Browser, Playwright, async_playwright

from .constraints import FlightRequest, parse_flight_request
from .planner import Planner
from .schemas import AgentTask, EventKind, FlightOption, RuntimeEvent, TaskStatus
from .tools import create_default_registry
from .db import SessionLocal
from .models import TaskModel, TaskEventModel


class TaskStore:
    """In-memory task store with per-task event streams.

    Replace this seam with Postgres/Redis before running distributed workers.
    """

    def __init__(self) -> None:
        self.tasks: dict[UUID, AgentTask] = {}
        self.streams: dict[UUID, asyncio.Queue[RuntimeEvent]] = {}

    async def create(self, task: AgentTask) -> None:
        self.tasks[task.id] = task
        self.streams.setdefault(task.id, asyncio.Queue())

        async with SessionLocal() as session:
            session.add(
                TaskModel(
                    id=task.id,
                    objective=task.objective,
                    start_url=task.start_url,
                    status=task.status.value,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()

    def get(self, task_id: UUID) -> AgentTask | None:
        return self.tasks.get(task_id)

    def list(self) -> list[AgentTask]:
        return sorted(self.tasks.values(), key=lambda task: task.created_at, reverse=True)

    async def emit(
        self,
        task: AgentTask,
        kind: EventKind,
        message: str,
        **data,
    ) -> None:
        event = RuntimeEvent(
            kind=kind,
            message=message,
            data=data,
        )
        self.tasks[task.id] = task
        task.events.append(event)
        task.updated_at = datetime.utcnow()
        
        queue = self.streams.setdefault(task.id, asyncio.Queue())
        await queue.put(event)

        async with SessionLocal() as session:
            session.add(
                TaskEventModel(
                    task_id=task.id,
                    kind=kind.value,
                    message=message,
                    data=data,
                    created_at=event.at,
                )
            )

            db_task = await session.get(TaskModel, task.id)
            if db_task:
                db_task.status = task.status.value
                db_task.result = task.result
                db_task.error = task.error
                db_task.artifact_path = task.artifact_path
                db_task.retries = data.get("retry", db_task.retries)
                db_task.updated_at = task.updated_at
                

            await session.commit()

    async def events(self, task_id: UUID) -> AsyncIterator[RuntimeEvent]:
        queue = self.streams[task_id]
        while True:
            yield await queue.get()


class BrowserManager:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.tools = create_default_registry()

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
            data = await self.tools.execute("navigate", page, url=url)
            return data["title"], data["url"]
        finally:
            await page.close()

    async def search_flights(
        self,
        url: str,
        request: FlightRequest,
        artifact_path: Path | None = None,
    ) -> tuple[str, str, list[FlightOption]]:
        """Run the bounded Cleartrip search flow; it never opens a booking flow."""

        if (
            not self._browser
            or not request.origin
            or not request.destination
            or not request.departure_date
        ):
            raise RuntimeError("Flight search requires complete trip constraints")

        try:
            departure = date.fromisoformat(request.departure_date)
        except ValueError as exc:
            raise RuntimeError(
                "Use an ISO departure date (YYYY-MM-DD) for flight search"
            ) from exc

        today = date.today()
        month_offset = (departure.year - today.year) * 12 + departure.month - today.month

        if month_offset not in (0, 1):
            raise RuntimeError(
                "Cleartrip safe executor currently supports dates in the next two visible calendar months"
            )

        page = await self._browser.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20_000)

            # dismiss overlays
            await self.tools.execute("dismiss_overlays", page)

            close = page.get_by_test_id("closeIcon")
            if await close.count() == 1:
                await close.click(force=True)

            for placeholder, city in (
                ("Where from?", request.origin),
                ("Where to?", request.destination),
            ):
                field = page.get_by_placeholder(placeholder)
                city_name, _, country = city.partition(",")

                await field.click()
                await field.fill(city_name.strip())

                matches: list[str] = []

                for _ in range(10):
                    option_texts = await page.locator("p").all_text_contents()

                    matches = [
                        text.strip()
                        for text in option_texts
                        if city_name.strip().lower() in text.lower()
                        and (
                            not country
                            or f", {country.strip().upper()}" in text.upper()
                        )
                    ]

                    if matches:
                        break

                    await page.wait_for_timeout(300)

                if not matches:
                    raise RuntimeError(
                        f"Could not find an airport suggestion for {city!r}"
                    )

                option = page.locator("p").filter(
                    has_text=re.compile(re.escape(matches[0]))
                )

                if await option.count() == 0:
                    raise RuntimeError(
                        f"Cleartrip airport suggestion for {city!r} was not actionable"
                    )

                target = option.first
                await target.scroll_into_view_if_needed()
                await target.click(force=True)

            await page.get_by_test_id("dateSelectOnward").click()

            days = page.locator(".day-gridContent").filter(
                has_text=re.compile(rf"^{departure.day}$")
            )

            if await days.count() <= month_offset:
                raise RuntimeError(
                    "Departure date is not available in Cleartrip's visible calendar"
                )

            await days.nth(month_offset).click()

            search = page.get_by_role("button", name="Search Flights")

            if await search.count() != 1:
                raise RuntimeError(
                    "Cleartrip search control could not be identified safely"
                )

            await search.click()

            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2500)

            text = await page.locator("body").inner_text()

            if "Enter departure and arrival airports" in text:
                raise RuntimeError("Cleartrip did not accept the selected airports")

            if artifact_path:
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(artifact_path), full_page=True)

            return (
                await page.title(),
                page.url,
                self._rank_flight_options(
                    self._extract_flight_options(text),
                    request,
                ),
            )

        finally:
            await page.close()
            
        
    @staticmethod
    def _rank_flight_options(
        options: list[FlightOption],
        request: FlightRequest,
    ) -> list[FlightOption]:
        def price_value(option: FlightOption) -> int:
            return int(re.sub(r"\D", "", option.price) or 0)

        def duration_minutes(option: FlightOption) -> int:
            hours, minutes = re.findall(r"\d+", option.duration)
            return int(hours) * 60 + int(minutes)

        def departure_key(option: FlightOption) -> str:
            return option.departure

        ranked = options

        if request.non_stop_only:
            ranked = [
                option
                for option in ranked
                if option.stops.lower() == "non stop"
            ]

        if request.sort_by == "duration":
            ranked = sorted(
                ranked,
                key=lambda option: (
                    duration_minutes(option),
                    price_value(option),
                ),
            )
        elif request.sort_by == "departure":
            ranked = sorted(
                ranked,
                key=lambda option: departure_key(option),
            )
        else:
            ranked = sorted(
                ranked,
                key=lambda option: (
                    price_value(option),
                    duration_minutes(option),
                ),
            )

        return ranked[:10]

    @staticmethod
    def _extract_flight_options(page_text: str) -> list[FlightOption]:
        # Normalize whitespace
        text = re.sub(r"\s+", " ", page_text)

        pattern = re.compile(
            r"(?:Partial Refundable )?"
            r"(?P<airline>[A-Za-z][A-Za-z &]+?) "
            r"(?P<flight_number>[A-Z0-9-]+) "
            r"(?P<departure>\d{2}:\d{2}) "
            r"(?P<duration>\d+h ?\d+m) "
            r"(?P<stops>Non[- ]?[Ss]top|\d+ ?[Ss]top[s]?) "
            r"(?P<arrival>\d{2}:\d{2})"
            r".*?"
            r"(?P<price>₹[\d,]+)",
            re.IGNORECASE,
        )

        options: list[FlightOption] = []

        for match in pattern.finditer(text):
            data = match.groupdict()

            stops = data["stops"]

            if re.search(r"non[- ]?stop", stops, re.IGNORECASE):
                stops = "Non Stop"
            else:
                stops = (
                    stops.replace("Stops", "stop")
                    .replace("stops", "stop")
                )

            options.append(
                FlightOption(
                    airline=data["airline"].strip(),
                    flight_number=data["flight_number"].strip(),
                    departure=data["departure"],
                    arrival=data["arrival"],
                    duration=data["duration"].strip(),
                    stops=stops,
                    price=data["price"],
                )
            )

        return options[:20]


    

class RuntimeState(TypedDict):
    task: AgentTask
    retries: int


class AgentRuntime:
    def __init__(self, store: TaskStore, browser: BrowserManager, planner: Planner) -> None:
        self.store = store
        self.browser = browser
        self.planner = planner
        self.workers: dict[UUID, asyncio.Task[None]] = {}
        self.max_retries = 2
        graph = StateGraph(RuntimeState)
        graph.add_node("planner", self._planner_node)
        graph.add_node("browser", self._browser_node)
        graph.add_node("critic", self._critic_node)
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "browser")
        graph.add_edge("browser", "critic")

        graph.add_conditional_edges(
            "critic",
            self._critic_router,
            {
                "planner": "planner",
                END: END,
            },
        )
        self.graph = graph.compile()

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
            await self.graph.ainvoke({"task": task, "retries": 0})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            await self.store.emit(task, EventKind.ERROR, "Task failed", error=str(exc))
        finally:
            self.workers.pop(task.id, None)

    async def _planner_node(self, state: RuntimeState) -> RuntimeState:
        task = state["task"]
        task.status = TaskStatus.PLANNING

        await self.store.emit(
            task,
            EventKind.SYSTEM,
            "Task accepted by LangGraph runtime",
        )

        plan = await self.planner.create(
            task.objective,
            task.start_url,
            task.max_steps,
            failure_context=task.error,
        )

        task.plan = plan.steps

        retries = state["retries"]

        if retries > 0:
            await self.store.emit(
                task,
                EventKind.RECOVERY,
                "Re-planning after recoverable failure",
                retry=retries,
                previous_error=task.error,
            )

        await self.store.emit(
            task,
            EventKind.PLAN,
            "Execution plan created",
            steps=task.plan,
            provider=plan.provider,
        )

        if plan.fallback_reason:
            await self.store.emit(
                task,
                EventKind.RECOVERY,
                "Model planner unavailable; using safe local fallback",
                reason=plan.fallback_reason,
            )

        await asyncio.sleep(0.35)
        return state
    
    async def _browser_node(self, state: RuntimeState) -> RuntimeState:
        task = state["task"]
        task.status = TaskStatus.RUNNING
        await self.store.emit(task, EventKind.ACTION, "Browser session allocated", headless=self.browser.headless)
        flight = parse_flight_request(task.objective)
        try:
            if flight and flight.missing:
                task.status = TaskStatus.NEEDS_INPUT
                missing = ", ".join(flight.missing)
                await self.store.emit(
                    task,
                    EventKind.RECOVERY,
                    "Travel constraints are incomplete; browser search paused",
                    missing=flight.missing,
                )
                task.result = f"I need the {missing} before searching flights. Add it to the objective and launch a new task; no booking or payment actions will be taken."
                return state
            if flight and task.start_url and "cleartrip.com" in task.start_url:
                await self.store.emit(
                    task,
                    EventKind.ACTION,
                    "Running bounded flight search (no booking or payment actions)",
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_date,
                )
                try:
                    artifact = Path(".runtime/artifacts") / f"{task.id}.png"
                    title, final_url, options = await self.browser.search_flights(task.start_url, flight, artifact)
                    task.flight_options = options
                    task.artifact_path = str(artifact)
                    await self.store.emit(task, EventKind.OBSERVATION, "Flight results page reached", title=title, url=final_url, options_found=len(options), sort_by=flight.sort_by, non_stop_only=flight.non_stop_only)
                    task.result = f"Found {len(options)} flight options for {flight.origin} to {flight.destination} on {flight.departure_date}. No booking or payment action was taken."
                    return state
                except Exception as exc:
                    task.status = TaskStatus.RECOVERING
                    task.error = str(exc)
                    state["retries"] += 1

                    await self.store.emit(
                        task,
                        EventKind.RECOVERY,
                        "Flight search could not be completed safely",
                        reason=str(exc),
                        retry=state["retries"],
                        max_retries=self.max_retries,
                    )

                    task.result = (
                        "The flight form could not be completed safely. "
                        "Attempting recovery through re-planning."
                    )

                    return state
            if task.start_url:
                await self.store.emit(task, EventKind.ACTION, "Navigating to starting URL", url=task.start_url)
                try:
                    title, final_url = await self.browser.observe(task.start_url)
                    await self.store.emit(task, EventKind.OBSERVATION, "Page observed", title=title, url=final_url)
                    task.result = f"Observed {title or 'page'} at {final_url}. Objective ready for model-guided continuation."
                except Exception as exc:
                        task.status = TaskStatus.RECOVERING
                        task.error = str(exc)
                        state["retries"] += 1

                        await self.store.emit(
                            task,
                            EventKind.RECOVERY,
                            "Navigation failed; retaining task context",
                            reason=str(exc),
                            retry=state["retries"],
                            max_retries=self.max_retries,
                        )

                        task.result = (
                            "The initial page could not be reached. "
                            "Attempting recovery through re-planning."
                        )
            else:
                await self.store.emit(task, EventKind.OBSERVATION, "No start URL supplied; plan is ready for a model-directed action")
                task.result = "Plan created. Provide a starting URL to begin a browser run."
            return state
        except Exception as exc:
            task.status = TaskStatus.RECOVERING
            task.error = str(exc)
            state["retries"] += 1
            task.result = (
                "The browser executor encountered an unexpected condition. "
                "Attempting recovery through re-planning."
            )
            await self.store.emit(task, EventKind.RECOVERY, "Browser executor requires recovery", reason=str(exc),
                retry=state["retries"], max_retries=self.max_retries)
            return state

    async def _critic_node(self, state: RuntimeState) -> RuntimeState:
        task = state["task"]
        retries = state["retries"]

        if task.status == TaskStatus.RECOVERING and retries < self.max_retries:
            await self.store.emit(
                task,
                EventKind.RECOVERY,
                "Critic requested another planning attempt",
                retry=retries,
                max_retries=self.max_retries,
            )
            return state

        if task.status in (TaskStatus.NEEDS_INPUT, TaskStatus.CANCELLED):
            return state

        if task.status == TaskStatus.RECOVERING and retries >= self.max_retries:
            task.status = TaskStatus.FAILED
            await self.store.emit(
                task,
                EventKind.ERROR,
                "Retry limit exhausted",
                retry=retries,
                max_retries=self.max_retries,
                error=task.error,
            )
            return state

        if not task.result:
            task.status = TaskStatus.FAILED
            task.error = "Critic received no executable result"
            await self.store.emit(task, EventKind.ERROR, "Critic rejected incomplete execution")
            return state

        await self.store.emit(
            task,
            EventKind.OBSERVATION,
            "Critic validated safe execution boundary",
            booking_or_payment_attempted=False,
        )

        task.status = TaskStatus.COMPLETED
        await self.store.emit(task, EventKind.SYSTEM, "Task completed", result=task.result)
        return state
    
    def _critic_router(self, state: RuntimeState):
        task = state["task"]
        retries = state["retries"]

        if task.status == TaskStatus.RECOVERING and retries < self.max_retries:
            return "planner"

        return END
