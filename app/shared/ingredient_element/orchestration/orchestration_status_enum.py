"""Closed StrEnum vocabularies for orchestration statuses."""

from enum import StrEnum


class OrchestrationStatus(StrEnum):
    """Full lifecycle states of an orchestration task."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrchestrationStartStatus(StrEnum):
    """Initial states returned immediately after starting a workflow."""

    QUEUED = "queued"
    RUNNING = "running"


class OrchestrationCancelStatus(StrEnum):
    """Terminal state returned after cancelling an orchestration task."""

    CANCELLED = "cancelled"
