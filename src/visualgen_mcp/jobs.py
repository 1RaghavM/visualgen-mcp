"""Thread-safe in-memory job store for video generation operations.

TODO: Replace with a SQLite-backed store if the server ever runs over HTTP
or needs to persist jobs across process restarts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any
from uuid import uuid4


class JobStatus(StrEnum):
    """Lifecycle states for a video generation job."""

    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Job:
    """A single video generation job."""

    job_id: str
    status: JobStatus
    model: str
    created_at: datetime
    operation: Any = None
    requested_duration_seconds: int = 0
    result_path: str | None = None
    error: str | None = None

    @property
    def elapsed_seconds(self) -> int:
        """Whole seconds since the job was submitted."""
        delta = datetime.now(UTC) - self.created_at
        return int(delta.total_seconds())


@dataclass
class JobStore:
    """In-memory, thread-safe job store keyed by job_id."""

    _jobs: dict[str, Job] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def create(
        self,
        *,
        model: str,
        operation: Any,
        requested_duration_seconds: int = 0,
    ) -> Job:
        """Register a new pending job and return it."""
        job = Job(
            job_id=str(uuid4()),
            status=JobStatus.PENDING,
            model=model,
            created_at=datetime.now(UTC),
            operation=operation,
            requested_duration_seconds=requested_duration_seconds,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        """Look up a job by id. Returns None if missing."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: Job) -> None:
        """Persist changes to a job already in the store."""
        with self._lock:
            self._jobs[job.job_id] = job

    def all(self) -> list[Job]:
        """Snapshot of every job in the store, newest first."""
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
