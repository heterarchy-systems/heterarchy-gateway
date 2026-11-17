"""Source-preserving applications for reviewer autonomy operations."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.inner_dto.autonomy_reviewer_inner_dto import (
    AssignedReviewerDto,
    AssignReviewerCommandDto,
    ExecutionAuthorDto,
    RecordedReviewVerdictDto,
    RecordReviewVerdictCommandDto,
    ResolvedAuthorDto,
    ReviewerAssignmentDto,
    ReviewerCandidateDto,
    ReviewerOperationResponseDto,
    VerifyNodeCompletionGateCommandDto,
    WorkCorrelationDto,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.types.autonomy.autonomy_reviewer_types import (
    ReviewerOperationResponseDict,
)
from app.orchestration.application.orchestration_command_utils import (
    execute_orchestration_operation,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_reviewer_schema import (
    AssignReviewerRequest,
    ExecutionAuthorSchema,
    RecordReviewVerdictRequest,
    ReviewerOperationResponse,
    VerifyNodeCompletionGateRequest,
    WorkCorrelationSchema,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling


def _work_correlation_dto(schema: WorkCorrelationSchema) -> WorkCorrelationDto:
    result = WorkCorrelationDto(
        goal_id=schema.goal_id,
        dag_revision=schema.dag_revision,
        node_id=schema.node_id,
        assignment_id=schema.assignment_id,
        attempt=schema.attempt,
    )
    return result


def _execution_author_dto(schema: ExecutionAuthorSchema) -> ExecutionAuthorDto:
    result = ExecutionAuthorDto(
        profile_id=schema.profile_id,
        participant_id=schema.participant_id,
        principal=schema.principal.to_inner_dto(),
    )
    return result


def _parse_reviewer_assignment_dto(
    schema: ReviewerOperationResponse,
) -> ReviewerAssignmentDto | None:
    assignment = schema.assignment
    if assignment is None:
        result = None
    else:
        verdict_schema = assignment.verdict
        verdict = (
            RecordedReviewVerdictDto(
                request_id=verdict_schema.request_id,
                outcome=verdict_schema.outcome,
                handoff_diff_digest_hex=verdict_schema.handoff_diff_digest_hex,
                rationale=verdict_schema.rationale,
                recorded_at_ms=verdict_schema.recorded_at_ms,
            )
            if verdict_schema is not None
            else None
        )
        result = ReviewerAssignmentDto(
            assignment_record_id=assignment.assignment_record_id,
            workspace_id=assignment.workspace_id,
            goal_id=assignment.goal_id,
            dag_revision=assignment.dag_revision,
            node_id=assignment.node_id,
            assignment_id=assignment.assignment_id,
            attempt=assignment.attempt,
            reviewer=AssignedReviewerDto(
                participation_id=assignment.reviewer.participation_id,
                profile_id=assignment.reviewer.profile_id,
                participant_id=assignment.reviewer.participant_id,
                principal=assignment.reviewer.principal.to_inner_dto(),
            ),
            executor=ResolvedAuthorDto(
                profile_id=assignment.executor.profile_id,
                participant_id=assignment.executor.participant_id,
                principal=assignment.executor.principal.to_inner_dto(),
            ),
            assigning_leader=ResolvedAuthorDto(
                profile_id=assignment.assigning_leader.profile_id,
                participant_id=assignment.assigning_leader.participant_id,
                principal=assignment.assigning_leader.principal.to_inner_dto(),
            ),
            qualification_domain=assignment.qualification_domain,
            rule_generation=assignment.rule_generation,
            revision=assignment.revision,
            assigned_at_ms=assignment.assigned_at_ms,
            verdict=verdict,
            replayed=assignment.replayed,
        )
    return result


def _reviewer_assignment_matches(
    assignment: ReviewerAssignmentDto,
    workspace_id: UUID,
    correlation: WorkCorrelationDto,
) -> bool:
    result = (
        assignment.assignment_record_id.int != 0
        and assignment.workspace_id == workspace_id
        and assignment.goal_id == correlation.goal_id
        and assignment.dag_revision == correlation.dag_revision
        and assignment.node_id == correlation.node_id
        and assignment.assignment_id == correlation.assignment_id
        and assignment.attempt == correlation.attempt
        and assignment.revision > 0
    )
    return result


def _validate_reviewer_response_status(
    status_code: int,
    response: ReviewerOperationResponseDict,
) -> None:
    assignment = response["assignment"]
    if status_code == status.HTTP_200_OK:
        if not response["admitted"] or response["rejectionCode"] is not None or assignment is None:
            raise ValueError("Successful reviewer response does not report an admitted assignment")
    elif status_code == status.HTTP_409_CONFLICT:
        if response["admitted"] or not response["rejectionCode"] or assignment is not None:
            raise ValueError("Reviewer conflict does not report a valid rejected outcome")
    else:
        raise ValueError("Unexpected reviewer result status")


def _validate_verdict_response_status(
    status_code: int,
    response: ReviewerOperationResponseDict,
) -> None:
    _validate_reviewer_response_status(status_code=status_code, response=response)
    assignment = response["assignment"]
    if status_code == status.HTTP_200_OK and assignment is not None:
        if assignment["verdict"] is None:
            raise ValueError("Recorded verdict response is missing its verdict receipt")


def _parse_reviewer_operation_response(
    payload: JsonValue,
    workspace_id: UUID,
    correlation: WorkCorrelationDto,
) -> ReviewerOperationResponseDict:
    schema = ReviewerOperationResponse.model_validate(payload)
    assignment = _parse_reviewer_assignment_dto(schema=schema)
    if schema.admitted and (assignment is None or schema.rejection_code is not None):
        raise ValueError("Admitted reviewer response is missing its assignment readback")
    if not schema.admitted and (assignment is not None or not schema.rejection_code):
        raise ValueError("Rejected reviewer response is missing its rejection code")
    if assignment is not None and not _reviewer_assignment_matches(
        assignment=assignment,
        workspace_id=workspace_id,
        correlation=correlation,
    ):
        raise ValueError("Reviewer assignment response escaped the requested path or work key")
    result = ReviewerOperationResponseDto(
        admitted=schema.admitted,
        rejection_code=schema.rejection_code,
        detail=schema.detail,
        assignment=assignment,
    ).to_dict()
    return result


def _source_assignment(
    schema: AssignReviewerRequest,
) -> AssignReviewerCommandDto:
    candidates = tuple(
        ReviewerCandidateDto(
            profile_id=candidate.profile_id,
            participant_id=candidate.participant_id,
            participation_id=candidate.participation_id,
            principal=candidate.principal.to_inner_dto(),
            agent_id=candidate.agent_id,
            session_id=candidate.session_id,
        )
        for candidate in schema.candidates
    )
    result = AssignReviewerCommandDto(
        request_id=schema.request_id,
        correlation=_work_correlation_dto(schema=schema.correlation),
        required_domain=schema.required_domain,
        executor=_execution_author_dto(schema=schema.executor),
        assigning_leader=_execution_author_dto(schema=schema.assigning_leader),
        candidates=candidates,
    )
    return result


def _source_verdict(
    schema: RecordReviewVerdictRequest,
) -> tuple[RecordReviewVerdictCommandDto, WorkCorrelationDto]:
    reviewer = (
        _execution_author_dto(schema=schema.reviewer) if schema.reviewer is not None else None
    )
    correlation = _work_correlation_dto(schema=schema.correlation)
    result = RecordReviewVerdictCommandDto(
        request_id=schema.request_id,
        correlation=correlation,
        expected_revision=schema.expected_revision,
        reviewer_agent_id=schema.reviewer_agent_id,
        reviewer_session_id=schema.reviewer_session_id,
        reviewer=reviewer,
        verdict=schema.verdict,
        handoff_diff_digest_hex=schema.handoff_diff_digest_hex,
    )
    return result, correlation


def _source_completion_gate(
    schema: VerifyNodeCompletionGateRequest,
) -> VerifyNodeCompletionGateCommandDto:
    result = VerifyNodeCompletionGateCommandDto(
        correlation=_work_correlation_dto(schema=schema.correlation),
        current_handoff_diff_digest_hex=schema.current_handoff_diff_digest_hex,
    )
    return result


class AutonomyReviewerApplication:
    """Execute reviewer assignment, verdict, and completion gate operations."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying this request's upstream authority.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def assign_reviewer(
        self,
        workspace_id: UUID,
        request: AssignReviewerRequest,
    ) -> OrchestrationOutcomeDto[ReviewerOperationResponseDict]:
        """Assign an independent reviewer to one exact work attempt.

        Args:
            workspace_id: Workspace identity selected by the public route.
            request: Strictly validated reviewer assignment request.
        Return:
            Source status and typed admitted or rejected reviewer outcome.
        """
        command = _source_assignment(schema=request)
        correlation = command.correlation
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/internal/v1/workspaces/{workspace_id}/reviewer-assignments",
            parse_result=partial(
                _parse_reviewer_operation_response,
                workspace_id=workspace_id,
                correlation=correlation,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_409_CONFLICT),
            validate_result_status=_validate_reviewer_response_status,
            workspace_id=workspace_id,
        )
        return result

    async def record_reviewer_verdict(
        self,
        workspace_id: UUID,
        request: RecordReviewVerdictRequest,
    ) -> OrchestrationOutcomeDto[ReviewerOperationResponseDict]:
        """Record an independent reviewer verdict for one exact diff.

        Args:
            workspace_id: Workspace identity selected by the public route.
            request: Strictly validated reviewer verdict request.
        Return:
            Source status and typed admitted or rejected reviewer outcome.
        """
        command, correlation = _source_verdict(schema=request)
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/internal/v1/workspaces/{workspace_id}/reviewer-verdicts",
            parse_result=partial(
                _parse_reviewer_operation_response,
                workspace_id=workspace_id,
                correlation=correlation,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_409_CONFLICT),
            validate_result_status=_validate_verdict_response_status,
            workspace_id=workspace_id,
        )
        return result

    async def verify_node_completion_gate(
        self,
        workspace_id: UUID,
        request: VerifyNodeCompletionGateRequest,
    ) -> OrchestrationOutcomeDto[ReviewerOperationResponseDict]:
        """Check the fail-closed review gate before node completion.

        Args:
            workspace_id: Workspace identity selected by the public route.
            request: Strictly validated completion gate request.
        Return:
            Source status and typed admitted or rejected reviewer outcome.
        """
        command = _source_completion_gate(schema=request)
        correlation = command.correlation
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/internal/v1/workspaces/{workspace_id}/node-completion-gate",
            parse_result=partial(
                _parse_reviewer_operation_response,
                workspace_id=workspace_id,
                correlation=correlation,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_409_CONFLICT),
            validate_result_status=_validate_reviewer_response_status,
            workspace_id=workspace_id,
        )
        return result
