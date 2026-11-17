"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.orchestration_execution_types import (
    PrincipalIdentityDict,
    PrincipalIdentityResultDict,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    UnixTimestampMs,
    UnsignedRevision,
    WorkAttempt,
)
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    ReviewVerdictOutcomeEnum,
)


class WorkCorrelationDict(TypedDict, total=True, closed=True):
    """Complete camelCase work correlation dictionary."""

    goalId: str
    dagRevision: DagRevision
    nodeId: str
    assignmentId: str
    attempt: WorkAttempt


class ExecutionAuthorDict(TypedDict, total=True, closed=True):
    """Three-axis execution author request dictionary."""

    profileId: str
    participantId: str
    principal: PrincipalIdentityDict


class ReviewerCandidateDict(TypedDict, total=True, closed=True):
    """Complete independent reviewer candidate dictionary."""

    profileId: str
    participantId: str
    participationId: str
    principal: PrincipalIdentityDict
    agentId: str
    sessionId: str


class AssignReviewerRequestDict(TypedDict, total=True, closed=True):
    """Complete independent reviewer assignment request dictionary."""

    requestId: str
    correlation: WorkCorrelationDict
    requiredDomain: str
    executor: ExecutionAuthorDict
    assigningLeader: ExecutionAuthorDict
    candidates: list[ReviewerCandidateDict]


class RecordReviewVerdictRequestDict(TypedDict, total=True, closed=True):
    """Complete diff-digest-bound reviewer verdict request dictionary."""

    requestId: str
    correlation: WorkCorrelationDict
    expectedRevision: UnsignedRevision
    reviewerAgentId: str
    reviewerSessionId: str
    reviewer: ExecutionAuthorDict | None
    verdict: ReviewVerdictOutcomeEnum
    handoffDiffDigestHex: str


class VerifyNodeCompletionGateRequestDict(TypedDict, total=True, closed=True):
    """Complete node completion gate request dictionary."""

    correlation: WorkCorrelationDict
    currentHandoffDiffDigestHex: str


class ResolvedAuthorDict(TypedDict, total=True, closed=True):
    """Resolved executor or assigning leader response dictionary."""

    profileId: str
    participantId: str
    principal: PrincipalIdentityResultDict


class AssignedReviewerDict(TypedDict, total=True, closed=True):
    """Resolved independent reviewer response dictionary."""

    participationId: str
    profileId: str
    participantId: str
    principal: PrincipalIdentityResultDict


class RecordedReviewVerdictDict(TypedDict, total=True, closed=True):
    """Recorded reviewer verdict response dictionary."""

    requestId: str
    outcome: ReviewVerdictOutcomeEnum
    handoffDiffDigestHex: str
    rationale: str
    recordedAtMs: UnixTimestampMs


class ReviewerAssignmentDict(TypedDict, total=True, closed=True):
    """Durable reviewer assignment response dictionary."""

    assignmentRecordId: str
    workspaceId: str
    goalId: str
    dagRevision: DagRevision
    nodeId: str
    assignmentId: str
    attempt: WorkAttempt
    reviewer: AssignedReviewerDict
    executor: ResolvedAuthorDict
    assigningLeader: ResolvedAuthorDict
    qualificationDomain: str | None
    ruleGeneration: UnsignedRevision | None
    revision: UnsignedRevision
    assignedAtMs: UnixTimestampMs
    verdict: RecordedReviewVerdictDict | None
    replayed: bool


class ReviewerOperationResponseDict(TypedDict, total=True, closed=True):
    """Typed admitted or rejected reviewer response dictionary."""

    admitted: bool
    rejectionCode: str | None
    detail: str | None
    assignment: ReviewerAssignmentDict | None
