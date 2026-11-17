"""Immutable DTOs for reviewer assignment, verdict, and completion gate."""

from dataclasses import dataclass
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    PrincipalIdentityDict,
    PrincipalIdentityDto,
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


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkCorrelationDto:
    """Immutable Workspace-relative work attempt coordinates."""

    goal_id: UUID
    dag_revision: DagRevision
    node_id: UUID
    assignment_id: UUID
    attempt: WorkAttempt

    def to_dict(self) -> WorkCorrelationDict:
        """Serialize work correlation using source camelCase keys.

        Args:
            None.
        Return:
            Complete work correlation dictionary.
        """
        result = WorkCorrelationDict(
            goalId=str(self.goal_id),
            dagRevision=self.dag_revision,
            nodeId=str(self.node_id),
            assignmentId=str(self.assignment_id),
            attempt=self.attempt,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionAuthorDto:
    """Immutable executor, assigning leader, or submitted reviewer identity."""

    profile_id: UUID
    participant_id: UUID
    principal: PrincipalIdentityDto

    def to_dict(self) -> ExecutionAuthorDict:
        """Serialize a three-axis execution author identity.

        Args:
            None.
        Return:
            Complete execution author dictionary.
        """
        result = ExecutionAuthorDict(
            profileId=str(self.profile_id),
            participantId=str(self.participant_id),
            principal=self.principal.to_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewerCandidateDto:
    """Immutable candidate identity used for reviewer assignment."""

    profile_id: UUID
    participant_id: UUID
    participation_id: UUID
    principal: PrincipalIdentityDto
    agent_id: UUID
    session_id: UUID

    def to_dict(self) -> ReviewerCandidateDict:
        """Serialize a reviewer candidate using source camelCase keys.

        Args:
            None.
        Return:
            Complete reviewer candidate dictionary.
        """
        result = ReviewerCandidateDict(
            profileId=str(self.profile_id),
            participantId=str(self.participant_id),
            participationId=str(self.participation_id),
            principal=self.principal.to_dict(),
            agentId=str(self.agent_id),
            sessionId=str(self.session_id),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class AssignReviewerCommandDto:
    """Immutable request to assign an independent reviewer."""

    request_id: UUID
    correlation: WorkCorrelationDto
    required_domain: str
    executor: ExecutionAuthorDto
    assigning_leader: ExecutionAuthorDto
    candidates: tuple[ReviewerCandidateDto, ...]

    def to_dict(self) -> AssignReviewerRequestDict:
        """Serialize reviewer assignment command wire fields.

        Args:
            None.
        Return:
            Complete reviewer assignment request dictionary.
        """
        result = AssignReviewerRequestDict(
            requestId=str(self.request_id),
            correlation=self.correlation.to_dict(),
            requiredDomain=self.required_domain,
            executor=self.executor.to_dict(),
            assigningLeader=self.assigning_leader.to_dict(),
            candidates=[candidate.to_dict() for candidate in self.candidates],
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordReviewVerdictCommandDto:
    """Immutable request to record a review verdict."""

    request_id: UUID
    correlation: WorkCorrelationDto
    expected_revision: UnsignedRevision
    reviewer_agent_id: UUID
    reviewer_session_id: UUID
    reviewer: ExecutionAuthorDto | None
    verdict: ReviewVerdictOutcomeEnum
    handoff_diff_digest_hex: str

    def to_dict(self) -> RecordReviewVerdictRequestDict:
        """Serialize a reviewer verdict command.

        Args:
            None.
        Return:
            Complete reviewer verdict request dictionary.
        """
        reviewer = self.reviewer.to_dict() if self.reviewer is not None else None
        result = RecordReviewVerdictRequestDict(
            requestId=str(self.request_id),
            correlation=self.correlation.to_dict(),
            expectedRevision=self.expected_revision,
            reviewerAgentId=str(self.reviewer_agent_id),
            reviewerSessionId=str(self.reviewer_session_id),
            reviewer=reviewer,
            verdict=self.verdict,
            handoffDiffDigestHex=self.handoff_diff_digest_hex,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class VerifyNodeCompletionGateCommandDto:
    """Immutable request to verify the node completion review gate."""

    correlation: WorkCorrelationDto
    current_handoff_diff_digest_hex: str

    def to_dict(self) -> VerifyNodeCompletionGateRequestDict:
        """Serialize the completion gate request.

        Args:
            None.
        Return:
            Complete completion gate request dictionary.
        """
        result = VerifyNodeCompletionGateRequestDict(
            correlation=self.correlation.to_dict(),
            currentHandoffDiffDigestHex=self.current_handoff_diff_digest_hex,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedAuthorDto:
    """Immutable response identity for an executor or leader."""

    profile_id: UUID
    participant_id: UUID
    principal: PrincipalIdentityDto

    def to_dict(self) -> ResolvedAuthorDict:
        """Serialize a resolved author response identity.

        Args:
            None.
        Return:
            Complete resolved author dictionary.
        """
        result = ResolvedAuthorDict(
            profileId=str(self.profile_id),
            participantId=str(self.participant_id),
            principal=self.principal.to_schema_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class AssignedReviewerDto:
    """Immutable response identity for the selected reviewer."""

    participation_id: UUID
    profile_id: UUID
    participant_id: UUID
    principal: PrincipalIdentityDto

    def to_dict(self) -> AssignedReviewerDict:
        """Serialize the selected reviewer identity.

        Args:
            None.
        Return:
            Complete assigned reviewer dictionary.
        """
        result = AssignedReviewerDict(
            participationId=str(self.participation_id),
            profileId=str(self.profile_id),
            participantId=str(self.participant_id),
            principal=self.principal.to_schema_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordedReviewVerdictDto:
    """Immutable diff-digest-bound reviewer verdict receipt."""

    request_id: UUID
    outcome: ReviewVerdictOutcomeEnum
    handoff_diff_digest_hex: str
    rationale: str
    recorded_at_ms: UnixTimestampMs

    def to_dict(self) -> RecordedReviewVerdictDict:
        """Serialize the recorded verdict receipt.

        Args:
            None.
        Return:
            Complete reviewer verdict response dictionary.
        """
        result = RecordedReviewVerdictDict(
            requestId=str(self.request_id),
            outcome=self.outcome,
            handoffDiffDigestHex=self.handoff_diff_digest_hex,
            rationale=self.rationale,
            recordedAtMs=self.recorded_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewerAssignmentDto:
    """Immutable durable reviewer assignment response."""

    assignment_record_id: UUID
    workspace_id: UUID
    goal_id: UUID
    dag_revision: DagRevision
    node_id: UUID
    assignment_id: UUID
    attempt: WorkAttempt
    reviewer: AssignedReviewerDto
    executor: ResolvedAuthorDto
    assigning_leader: ResolvedAuthorDto
    qualification_domain: str | None
    rule_generation: UnsignedRevision | None
    revision: UnsignedRevision
    assigned_at_ms: UnixTimestampMs
    verdict: RecordedReviewVerdictDto | None
    replayed: bool

    def to_dict(self) -> ReviewerAssignmentDict:
        """Serialize the durable reviewer assignment projection.

        Args:
            None.
        Return:
            Complete reviewer assignment response dictionary.
        """
        verdict = self.verdict.to_dict() if self.verdict is not None else None
        result = ReviewerAssignmentDict(
            assignmentRecordId=str(self.assignment_record_id),
            workspaceId=str(self.workspace_id),
            goalId=str(self.goal_id),
            dagRevision=self.dag_revision,
            nodeId=str(self.node_id),
            assignmentId=str(self.assignment_id),
            attempt=self.attempt,
            reviewer=self.reviewer.to_dict(),
            executor=self.executor.to_dict(),
            assigningLeader=self.assigning_leader.to_dict(),
            qualificationDomain=self.qualification_domain,
            ruleGeneration=self.rule_generation,
            revision=self.revision,
            assignedAtMs=self.assigned_at_ms,
            verdict=verdict,
            replayed=self.replayed,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewerOperationResponseDto:
    """Immutable admitted or rejected reviewer operation response."""

    admitted: bool
    rejection_code: str | None
    detail: str | None
    assignment: ReviewerAssignmentDto | None

    def to_dict(self) -> ReviewerOperationResponseDict:
        """Serialize the typed reviewer operation result.

        Args:
            None.
        Return:
            Complete reviewer operation response dictionary.
        """
        assignment = self.assignment.to_dict() if self.assignment is not None else None
        result = ReviewerOperationResponseDict(
            admitted=self.admitted,
            rejectionCode=self.rejection_code,
            detail=self.detail,
            assignment=assignment,
        )
        return result
