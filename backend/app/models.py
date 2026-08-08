import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    objective: Mapped[str] = mapped_column(Text)

    start_url: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(32))

    result: Mapped[str | None] = mapped_column(Text)

    error: Mapped[str | None] = mapped_column(Text)

    artifact_path: Mapped[str | None] = mapped_column(Text)

    retries: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime)

    updated_at: Mapped[datetime] = mapped_column(DateTime)

    events: Mapped[list["TaskEventModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskEventModel(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
    )

    kind: Mapped[str] = mapped_column(String(32))

    message: Mapped[str] = mapped_column(Text)

    data: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    task: Mapped[TaskModel] = relationship(back_populates="events")