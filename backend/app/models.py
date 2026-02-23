# backend/app/models.py
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class AnalysisJob(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    url: str
    status: JobStatus = Field(default=JobStatus.QUEUED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    verdict: str | None = None
    risk_score: int | None = None
    summary: str | None = None