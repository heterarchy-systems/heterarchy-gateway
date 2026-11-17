"""Closed wire vocabularies for Orchestration realtime events."""

from enum import IntEnum, StrEnum


class RealtimeEventKindEnum(StrEnum):
    """Source event kinds serialized as snake-case values."""

    AGENT_STATE_CHANGED = "agent_state_changed"
    AGENT_PROFILE_STATE_CHANGED = "agent_profile_state_changed"
    LOGICAL_SESSION_CHANGED = "logical_session_changed"
    TEAM_CHANGED = "team_changed"
    MEMBERSHIP_CHANGED = "membership_changed"
    LEADERSHIP_CHANGED = "leadership_changed"
    PROVISIONING_STATE_CHANGED = "provisioning_state_changed"
    APPROVAL_REQUEST_CHANGED = "approval_request_changed"
    APPROVAL_DECISION_CHANGED = "approval_decision_changed"
    APPROVAL_POLICY_CHANGED = "approval_policy_changed"
    AGENT_REQUEST_STATE_CHANGED = "agent_request_state_changed"
    SCHEDULING_CHANGED = "scheduling_changed"
    WORKSPACE_SCOPE_CHANGED = "workspace_scope_changed"
    REVIEWER_ASSIGNMENT_CHANGED = "reviewer_assignment_changed"
    REVIEWER_VERDICT_RECORDED = "reviewer_verdict_recorded"
    EXECUTION_SNAPSHOT_COMMITTED = "execution_snapshot_committed"
    SWARM_RUN_CHANGED = "swarm_run_changed"
    SWARM_CHANNEL_CHANGED = "swarm_channel_changed"
    SWARM_MEMBER_STATE_CHANGED = "swarm_member_state_changed"
    SWARM_BOARD_MESSAGE_POSTED = "swarm_board_message_posted"
    SWARM_VERDICT_RECORDED = "swarm_verdict_recorded"
    SWARM_STALL_EVALUATED = "swarm_stall_evaluated"
    SETTLEMENT_PROJECTED = "settlement_projected"


class RealtimeResyncUnitReasonEnum(StrEnum):
    """Source resync reasons serialized as plain enum strings."""

    HUB_CLOSED = "hub_closed"
    SERVER_SHUTDOWN = "server_shutdown"
    ACCESS_REVOKED = "access_revoked"
    AUTHORITY_UNAVAILABLE = "authority_unavailable"
    OBSERVATION_GAP = "observation_gap"


class RealtimeSseEventNameEnum(StrEnum):
    """SSE event names assigned by the Orchestration source."""

    STATE_CHANGED = "state_changed"
    RESYNC_REQUIRED = "resync_required"


class RealtimeSseFrameKindEnum(StrEnum):
    """Internal frame categories for bounded SSE relay ownership."""

    EVENT = "event"
    RESYNC = "resync"
    COMMENT = "comment"
    END = "end"


class RealtimeEventDispositionEnum(StrEnum):
    """Source event ordering decisions owned by the bounded relay."""

    DUPLICATE = "duplicate"
    RESUME_FENCED = "resume_fenced"
    NEW = "new"


class RealtimeHeaderNameEnum(StrEnum):
    """HTTP header names owned by the Orchestration event transport."""

    ACCEPT = "accept"
    ACCEPT_ENCODING = "accept-encoding"
    AUTHORIZATION = "authorization"
    CACHE_CONTROL = "cache-control"
    CONTENT_ENCODING = "content-encoding"
    CONTENT_TYPE = "content-type"
    LAST_EVENT_ID = "last-event-id"
    RETRY_AFTER = "retry-after"
    SESSION_ID = "x-orchestration-session-id"
    X_ACCEL_BUFFERING = "x-accel-buffering"


class RealtimeMediaTypeEnum(StrEnum):
    """Media types emitted or accepted by the realtime transport."""

    EVENT_STREAM = "text/event-stream"


class RealtimeContentEncodingEnum(StrEnum):
    """The one accepted source event-stream content encoding."""

    IDENTITY = "identity"


class RealtimeCacheControlEnum(StrEnum):
    """Cache behavior for downstream realtime stream responses."""

    NO_CACHE = "no-cache"


class RealtimeProxyBufferingEnum(StrEnum):
    """Reverse-proxy behavior required for incremental SSE delivery."""

    DISABLED = "no"


class RealtimeQueueEventCapacityEnum(IntEnum):
    """Maximum complete frames retained for one Gateway subscriber."""

    MAX_EVENTS = 64


class RealtimeQueueByteCapacityEnum(IntEnum):
    """Maximum serialized bytes retained in one Gateway frame queue."""

    MAX_BYTES = 1_048_576


class RealtimeFrameByteLimitEnum(IntEnum):
    """Maximum UTF-8 size of one complete source or Gateway SSE frame."""

    MAX_BYTES = 16_384


class RealtimeSourceChunkByteLimitEnum(IntEnum):
    """Maximum raw chunk accepted by the incremental SSE parser."""

    MAX_BYTES = 4_096


class RealtimeAdmissionErrorByteLimitEnum(IntEnum):
    """Maximum buffered JSON body for a pre-stream source rejection."""

    MAX_BYTES = 1_048_576


class RealtimeSendTimeoutMsEnum(IntEnum):
    """Maximum time allowed for one downstream ASGI send."""

    TIMEOUT_MS = 30_000


class RealtimeSourceReadTimeoutSecondsEnum(IntEnum):
    """Read idle timeout above the source's fifteen-second keepalive cadence."""

    IDLE_TIMEOUT_SECONDS = 45


class RealtimeCursorComponentDigitsEnum(IntEnum):
    """Maximum decimal digits in one unsigned 64-bit cursor component."""

    MAX_DIGITS = 20


class RealtimeRetryDigitLimitEnum(IntEnum):
    """Maximum decimal digits accepted for an SSE retry hint."""

    MAX_DIGITS = 10


class RealtimeResyncRetryMsEnum(IntEnum):
    """Source retry hint carried on terminal resynchronization events."""

    RETRY_MS = 2_000
