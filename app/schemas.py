from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    open = "open"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    completed_at: datetime | None = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=80)
    description: str = Field(default="", max_length=200)
    priority: TaskPriority = TaskPriority.medium
