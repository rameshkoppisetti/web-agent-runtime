from __future__ import annotations

import os
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .planner import Planner
from .runtime import AgentRuntime, BrowserManager, TaskStore
from .schemas import AgentTask, CreateTaskRequest, HealthResponse

store = TaskStore()
browser = BrowserManager(headless=os.getenv("HEADLESS", "true").lower() == "true")
runtime = AgentRuntime(store, browser, Planner())


@asynccontextmanager
async def lifespan(_: FastAPI):
    await browser.start()
    yield
    await browser.stop()


app = FastAPI(title="WebAgent Runtime", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://0.0.0.0:5173",
    ).split(","),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(browser="ready" if browser._browser else "starting")


@app.get("/api/tasks", response_model=list[AgentTask])
async def list_tasks() -> list[AgentTask]:
    return store.list()


@app.post("/api/tasks", response_model=AgentTask, status_code=201)
async def create_task(payload: CreateTaskRequest) -> AgentTask:
    task = store.create(AgentTask(objective=payload.objective, start_url=str(payload.start_url) if payload.start_url else None, max_steps=payload.max_steps))
    runtime.launch(task)
    return task


@app.get("/api/tasks/{task_id}", response_model=AgentTask)
async def get_task(task_id: UUID) -> AgentTask:
    task = store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@app.post("/api/tasks/{task_id}/cancel", response_model=AgentTask)
async def cancel_task(task_id: UUID) -> AgentTask:
    task = store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    await runtime.cancel(task)
    return task


@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: UUID) -> StreamingResponse:
    task = store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    async def stream():
        for event in task.events:
            yield f"data: {event.model_dump_json()}\n\n"
        queue = store.streams[task_id]
        while not queue.empty():
            queue.get_nowait()
        async for event in store.events(task_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
