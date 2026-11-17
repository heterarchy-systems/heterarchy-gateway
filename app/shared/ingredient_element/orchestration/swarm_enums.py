"""Closed Swarm vocabularies mirrored from Orchestration wire output."""

from enum import StrEnum


class SwarmRunModeEnum(StrEnum):
    """Canonical Swarm run mode discriminators."""

    STANDALONE = "STANDALONE"
    DAG_NODE_HYBRID = "DAG_NODE_HYBRID"


class SwarmRunStateEnum(StrEnum):
    """Durable Swarm run lifecycle states."""

    ACTIVE = "ACTIVE"
    CONVERGING = "CONVERGING"
    CANDIDATE_READY = "CANDIDATE_READY"
    SETTLED = "SETTLED"
    ABORTED = "ABORTED"


class SwarmRoleKindEnum(StrEnum):
    """Closed roles available to Swarm members."""

    COORDINATOR = "COORDINATOR"
    WORKER = "WORKER"
    HELPER = "HELPER"
    VERIFIER = "VERIFIER"
    MONITOR = "MONITOR"


class SwarmWorkspaceModeEnum(StrEnum):
    """Closed Swarm member workspace isolation modes."""

    INHERIT = "INHERIT"
    SHARE = "SHARE"
    BRANCH = "BRANCH"


class SwarmMemberStateEnum(StrEnum):
    """Durable execution and wakeup states of a Swarm member."""

    WAITING = "WAITING"
    WAKE_QUEUED = "WAKE_QUEUED"
    WORKING = "WORKING"
    SUSPENDED_QUOTA = "SUSPENDED_QUOTA"
    STOPPED = "STOPPED"
    KILLED = "KILLED"


class SwarmDoorbellReasonEnum(StrEnum):
    """Canonical causes recorded for Swarm wakeup doorbells."""

    DIRECT_MENTION = "DIRECT_MENTION"
    CHANNEL_MENTION = "CHANNEL_MENTION"
    ALL_MENTION = "ALL_MENTION"
    SYSTEM_STALL = "SYSTEM_STALL"
    SYSTEM_LIVELOCK = "SYSTEM_LIVELOCK"
    MANUAL_WAKE = "MANUAL_WAKE"


class SwarmPanelSeatKindEnum(StrEnum):
    """Closed seat kinds in a verification panel."""

    AUTHOR = "AUTHOR"
    VERIFIER = "VERIFIER"


class SwarmVerdictOutcomeEnum(StrEnum):
    """Canonical review verdict outcomes recorded by Swarm."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_CHANGES = "NEEDS_CHANGES"


class SwarmTurnFailureDispositionEnum(StrEnum):
    """Canonical dispositions for failed or quota-suspended turns."""

    TRANSIENT_RETRY = "TRANSIENT_RETRY"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    STOPPED = "STOPPED"


class SwarmConvergenceTargetEnum(StrEnum):
    """Explicit targets for Swarm convergence requests."""

    CANDIDATE_READY = "CANDIDATE_READY"
    SETTLED = "SETTLED"
