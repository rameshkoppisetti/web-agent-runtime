from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class TaskStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventKind(StrEnum):
    SYSTEM = "system"
    PLAN = "plan"
    ACTION = "action"
    OBSERVATION = "observation"
    RECOVERY = "recovery"
    ERROR = "error"


class CreateTaskRequest(BaseModel):
    objective: str = Field(min_length=5, max_length=2000)
    start_url: HttpUrl | None = None
    max_steps: int = Field(default=8, ge=1, le=30)


class RuntimeEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    at: datetime = Field(default_factory=datetime.utcnow)
    kind: EventKind
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    objective: str
    start_url: str | None = None
    max_steps: int = 8
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    plan: list[str] = Field(default_factory=list)
    events: list[RuntimeEvent] = Field(default_factory=list)
    result: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    browser: str
