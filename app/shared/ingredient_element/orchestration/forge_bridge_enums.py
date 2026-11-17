"""Closed East-West Forge bridge wire key vocabularies."""

from enum import StrEnum


class ForgeBridgeFieldEnum(StrEnum):
    """JSON keys shared by the three Orchestration bridge operations."""

    REQUEST_ID = "requestId"
    SESSION_ID = "sessionId"
    CANDIDATE_MEMBER_IDS = "candidateMemberIds"
    STAGE_CANDIDATE_ONLY = "stageCandidateOnly"
    RUN = "run"
    CHANGED_FILES = "changedFiles"
    GATE = "gate"
    ACTIVITY_ID = "activityId"
    COORDINATOR_AGENT_ID = "coordinatorAgentId"
    OUTBOX_MIGRATION_ID = "outboxMigrationId"
    OUTBOX_AFTER_SEQUENCE = "outboxAfterSequence"
    PURGE_EPHEMERAL = "purgeEphemeral"
    SETTLEMENT_ID = "settlementId"
    SETTLED_FILE_COUNT = "settledFileCount"
    SETTLED_AT_MS = "settledAtMs"
    OUTBOX_SEQUENCE = "outboxSequence"
    OUTBOX_SYNC = "outboxSync"
    PURGED_EPHEMERAL = "purgedEphemeral"
    MIGRATION_ID = "migrationId"
    AFTER_SEQUENCE = "afterSequence"
    LIMIT = "limit"
    APPLIED_COUNT = "appliedCount"
    DAG_SETTLED_COUNT = "dagSettledCount"
    SWARM_SETTLED_COUNT = "swarmSettledCount"
    LAST_SEQUENCE = "lastSequence"
