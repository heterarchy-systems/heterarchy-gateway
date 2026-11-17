"""Strict request and response schemas for reviewer autonomy operations."""

from functools import partial
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.orchestration.schema.execution.orchestration_execution_schema import (
    PrincipalIdentitySchema,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    Sha256DigestHex,
    UnixTimestampMs,
    UnsignedRevision,
    WorkAttempt,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    ReviewVerdictOutcomeEnum,
)
from app.shared.types.wire_scalar_types import WireUUID, parse_wire_enum

type ReviewVerdictOutcome = Annotated[
    ReviewVerdictOutcomeEnum,
    BeforeValidator(partial(parse_wire_enum, ReviewVerdictOutcomeEnum)),
]


class WorkCorrelationSchema(StrictSchemaModel):
    """Identify one Workspace, Goal, DAG node, assignment, and attempt."""

    goal_id: Annotated[WireUUID, Field(description="Goal identity.", alias="goalId")]
    dag_revision: Annotated[
        DagRevision,
        Field(description="Positive DAG revision.", alias="dagRevision"),
    ]
    node_id: Annotated[WireUUID, Field(description="DAG node identity.", alias="nodeId")]
    assignment_id: Annotated[
        WireUUID,
        Field(description="Agent assignment identity.", alias="assignmentId"),
    ]
    attempt: Annotated[
        WorkAttempt,
        Field(description="Zero-based execution attempt."),
    ]


class ExecutionAuthorSchema(StrictSchemaModel):
    """Identify one executor, assigning leader, or submitted reviewer."""

    profile_id: Annotated[
        WireUUID,
        Field(description="Agent Profile identity.", alias="profileId"),
    ]
    participant_id: Annotated[
        WireUUID,
        Field(description="Workspace participant identity.", alias="participantId"),
    ]
    principal: Annotated[
        PrincipalIdentitySchema,
        Field(description="Authenticated principal identity."),
    ]


class ReviewerCandidateSchema(StrictSchemaModel):
    """Represent one candidate in independent reviewer selection."""

    profile_id: Annotated[
        WireUUID,
        Field(description="Candidate Agent Profile identity.", alias="profileId"),
    ]
    participant_id: Annotated[
        WireUUID,
        Field(description="Candidate Workspace participant identity.", alias="participantId"),
    ]
    participation_id: Annotated[
        WireUUID,
        Field(description="Candidate Workspace participation identity.", alias="participationId"),
    ]
    principal: Annotated[
        PrincipalIdentitySchema,
        Field(description="Candidate authenticated principal identity."),
    ]
    agent_id: Annotated[
        WireUUID,
        Field(description="Candidate agent instance identity.", alias="agentId"),
    ]
    session_id: Annotated[
        WireUUID,
        Field(description="Candidate agent session identity.", alias="sessionId"),
    ]


class AssignReviewerRequest(StrictSchemaModel):
    """Request deterministic independent reviewer assignment."""

    request_id: Annotated[
        WireUUID,
        Field(description="Stable request identity.", alias="requestId"),
    ]
    correlation: Annotated[
        WorkCorrelationSchema,
        Field(description="Workspace-relative work attempt coordinates."),
    ]
    required_domain: Annotated[
        str,
        Field(description="Required reviewer qualification domain.", alias="requiredDomain"),
    ]
    executor: Annotated[
        ExecutionAuthorSchema,
        Field(description="Three-axis executor identity."),
    ]
    assigning_leader: Annotated[
        ExecutionAuthorSchema,
        Field(description="Three-axis assigning leader identity.", alias="assigningLeader"),
    ]
    candidates: Annotated[
        list[ReviewerCandidateSchema],
        Field(description="Ordered candidate reviewer identities."),
    ]


class RecordReviewVerdictRequest(StrictSchemaModel):
    """Record a reviewer verdict tied to an exact handoff diff digest."""

    request_id: Annotated[
        WireUUID,
        Field(description="Stable request identity.", alias="requestId"),
    ]
    correlation: Annotated[
        WorkCorrelationSchema,
        Field(description="Workspace-relative work attempt coordinates."),
    ]
    expected_revision: Annotated[
        UnsignedRevision,
        Field(
            description="Expected positive reviewer-assignment revision.",
            gt=0,
            alias="expectedRevision",
        ),
    ]
    reviewer_agent_id: Annotated[
        WireUUID,
        Field(description="Assigned reviewer agent identity.", alias="reviewerAgentId"),
    ]
    reviewer_session_id: Annotated[
        WireUUID,
        Field(description="Assigned reviewer session identity.", alias="reviewerSessionId"),
    ]
    reviewer: Annotated[
        ExecutionAuthorSchema | None,
        Field(description="Optional submitted reviewer identity."),
    ]
    verdict: Annotated[
        ReviewVerdictOutcome,
        Field(description="Recorded reviewer verdict."),
    ]
    handoff_diff_digest_hex: Annotated[
        Sha256DigestHex,
        Field(
            description="Lowercase SHA-256 digest of the reviewed handoff diff.",
            alias="handoffDiffDigestHex",
        ),
    ]


class VerifyNodeCompletionGateRequest(StrictSchemaModel):
    """Verify the independent review gate for one exact diff digest."""

    correlation: Annotated[
        WorkCorrelationSchema,
        Field(description="Workspace-relative work attempt coordinates."),
    ]
    current_handoff_diff_digest_hex: Annotated[
        Sha256DigestHex,
        Field(
            description="Current lowercase handoff diff SHA-256 digest.",
            alias="currentHandoffDiffDigestHex",
        ),
    ]


class ResolvedAuthorSchema(StrictSchemaModel):
    """Response identity for an executor or assigning leader."""

    profile_id: Annotated[
        WireUUID,
        Field(description="Agent Profile identity.", alias="profileId"),
    ]
    participant_id: Annotated[
        WireUUID,
        Field(description="Workspace participant identity.", alias="participantId"),
    ]
    principal: Annotated[
        PrincipalIdentitySchema,
        Field(description="Authenticated principal identity."),
    ]


class AssignedReviewerSchema(StrictSchemaModel):
    """Response identity for an assigned independent reviewer."""

    participation_id: Annotated[
        WireUUID,
        Field(description="Workspace participation identity.", alias="participationId"),
    ]
    profile_id: Annotated[
        WireUUID,
        Field(description="Agent Profile identity.", alias="profileId"),
    ]
    participant_id: Annotated[
        WireUUID,
        Field(description="Workspace participant identity.", alias="participantId"),
    ]
    principal: Annotated[
        PrincipalIdentitySchema,
        Field(description="Authenticated principal identity."),
    ]


class RecordedReviewVerdictSchema(StrictSchemaModel):
    """Response receipt for a diff-digest-bound reviewer verdict."""

    request_id: Annotated[
        WireUUID,
        Field(description="Verdict request identity.", alias="requestId"),
    ]
    outcome: Annotated[
        ReviewVerdictOutcome,
        Field(description="Canonical recorded verdict outcome."),
    ]
    handoff_diff_digest_hex: Annotated[
        Sha256DigestHex,
        Field(description="Reviewed handoff diff SHA-256 digest.", alias="handoffDiffDigestHex"),
    ]
    rationale: Annotated[str, Field(description="Source-generated verdict rationale.")]
    recorded_at_ms: Annotated[
        UnixTimestampMs,
        Field(description="Verdict recording time in Unix milliseconds.", alias="recordedAtMs"),
    ]


class ReviewerAssignmentSchema(StrictSchemaModel):
    """Response projection of one durable reviewer assignment."""

    assignment_record_id: Annotated[
        WireUUID,
        Field(
            description="Durable reviewer assignment record identity.", alias="assignmentRecordId"
        ),
    ]
    workspace_id: Annotated[
        WireUUID,
        Field(description="Workspace identity.", alias="workspaceId"),
    ]
    goal_id: Annotated[WireUUID, Field(description="Goal identity.", alias="goalId")]
    dag_revision: Annotated[
        DagRevision,
        Field(description="DAG revision for the assignment.", alias="dagRevision"),
    ]
    node_id: Annotated[WireUUID, Field(description="DAG node identity.", alias="nodeId")]
    assignment_id: Annotated[
        WireUUID,
        Field(description="Agent assignment identity.", alias="assignmentId"),
    ]
    attempt: Annotated[
        WorkAttempt,
        Field(description="Zero-based execution attempt."),
    ]
    reviewer: Annotated[
        AssignedReviewerSchema,
        Field(description="Selected independent reviewer identity."),
    ]
    executor: Annotated[
        ResolvedAuthorSchema,
        Field(description="Resolved executor identity."),
    ]
    assigning_leader: Annotated[
        ResolvedAuthorSchema,
        Field(description="Resolved assigning leader identity.", alias="assigningLeader"),
    ]
    qualification_domain: Annotated[
        str | None,
        Field(
            description="Qualification domain used for assignment, or null.",
            alias="qualificationDomain",
        ),
    ]
    rule_generation: Annotated[
        UnsignedRevision | None,
        Field(description="Qualification rule generation, or null.", alias="ruleGeneration"),
    ]
    revision: Annotated[
        UnsignedRevision,
        Field(description="Durable assignment revision."),
    ]
    assigned_at_ms: Annotated[
        UnixTimestampMs,
        Field(description="Assignment time in Unix milliseconds.", alias="assignedAtMs"),
    ]
    verdict: Annotated[
        RecordedReviewVerdictSchema | None,
        Field(description="Latest recorded verdict, or null."),
    ]
    replayed: Annotated[
        bool,
        Field(description="Whether this response replays an existing assignment."),
    ]


class ReviewerOperationResponse(StrictSchemaModel):
    """Typed admitted or rejected result for reviewer operations."""

    admitted: Annotated[bool, Field(description="Whether the reviewer operation was admitted.")]
    rejection_code: Annotated[
        str | None,
        Field(description="Stable rejection code, or null.", alias="rejectionCode"),
    ]
    detail: Annotated[str | None, Field(description="Rejection detail, or null.")]
    assignment: Annotated[
        ReviewerAssignmentSchema | None,
        Field(description="Assignment readback, or null."),
    ]
