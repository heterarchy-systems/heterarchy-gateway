"""Closed wire vocabularies for Orchestration autonomy contracts."""

from enum import StrEnum


class ExecutionSnapshotQueryFieldEnum(StrEnum):
    """Wire fields echoed by an execution snapshot readback."""

    WORKSPACE_ID = "workspaceId"
    GOAL_ID = "goalId"
    DAG_REVISION = "dagRevision"
    NODE_ID = "nodeId"
    ASSIGNMENT_ID = "assignmentId"
    ATTEMPT = "attempt"
    RECORD = "record"


class ReviewVerdictOutcomeEnum(StrEnum):
    """Accepted outcomes for an independent reviewer verdict."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"


class LaunchLedgerStatusEnum(StrEnum):
    """Recorded states of an execution snapshot launch-ledger row."""

    PREPARED = "PREPARED"
    NOT_STARTED = "NOT_STARTED"
    SPAWNED = "SPAWNED"
    EXITED = "EXITED"
    UNKNOWN = "UNKNOWN"


class LaunchUnknownReasonEnum(StrEnum):
    """Closed source reasons for unknown launch-ledger execution states."""

    BOOT_RECOVERY_AFTER_SPAWN = "BOOT_RECOVERY_AFTER_SPAWN"
    EXECUTION_TIMED_OUT = "EXECUTION_TIMED_OUT"
    OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"
    FORCED_TERMINATION = "FORCED_TERMINATION"
