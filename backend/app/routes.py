from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select

from .db import SessionLocal
from .models import TaskEventModel
from .schemas import AgentTask, CreateTaskRequest, HealthResponse

router = APIRouter()


def configure_routes(router_state):
    store = router_state["store"]
    runtime = router_state["runtime"]
    browser = router_state["browser"]

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(browser="ready" if browser._browser else "starting")

    @router.get("/api/tools")
    async def list_tools():
        return browser.tools.list_tools()

    @router.get("/api/tasks", response_model=list[AgentTask])
    async def list_tasks() -> list[AgentTask]:
        return store.list()

    @router.post("/api/tasks", response_model=AgentTask, status_code=201)
    async def create_task(payload: CreateTaskRequest) -> AgentTask:
        task = AgentTask(
            objective=payload.objective,
            start_url=str(payload.start_url) if payload.start_url else None,
            max_steps=payload.max_steps,
        )

        await store.create(task)
        runtime.launch(task)
        return task

    @router.get("/api/tasks/{task_id}", response_model=AgentTask)
    async def get_task(task_id: UUID) -> AgentTask:
        task = store.get(task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        return task

    @router.get("/api/tasks/{task_id}/artifact")
    async def get_task_artifact(task_id: UUID) -> FileResponse:
        task = store.get(task_id)
        if not task or not task.artifact_path:
            raise HTTPException(404, "Artifact not found")

        path = Path(task.artifact_path)
        if not path.exists():
            raise HTTPException(404, "Artifact file not found")

        return FileResponse(path, media_type="image/png", filename=f"task-{task_id}.png")

    @router.post("/api/tasks/{task_id}/cancel", response_model=AgentTask)
    async def cancel_task(task_id: UUID) -> AgentTask:
        task = store.get(task_id)
        if not task:
            raise HTTPException(404, "Task not found")

        await runtime.cancel(task)
        return task

    @router.get("/api/tasks/{task_id}/events")
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

    @router.get("/api/tasks/{task_id}/history")
    async def task_history(task_id: UUID):
        async with SessionLocal() as session:
            result = await session.execute(
                select(TaskEventModel)
                .where(TaskEventModel.task_id == task_id)
                .order_by(TaskEventModel.id)
            )
            events = result.scalars().all()

        return [
            {
                "kind": e.kind,
                "message": e.message,
                "data": e.data,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]