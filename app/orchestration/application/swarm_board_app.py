"""Pure request forwarding and source-contract checks for Swarm board APIs."""

from functools import partial
from uuid import UUID

from fastapi import status

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.swarm_board_inner_dto import (
    ConvergeSwarmResponseDict,
    PostSwarmMessageResponseDict,
    SwarmBoardPageResponseDict,
    SwarmStallCheckResponseDict,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    SwarmRunDict,
    SwarmVerdictDict,
    SwarmVerificationPanelDict,
)
from app.orchestration.application.orchestration_command_utils import (
    ORCHESTRATION_SWARM_EXCHANGE_POLICY,
    execute_orchestration_operation,
)
from app.orchestration.application.swarm_board_parsers import (
    parse_abort_result,
    parse_board_page_result,
    parse_convergence_result,
    parse_panel_result,
    parse_post_message_result,
    parse_settlement_result,
    parse_stall_check_result,
    parse_verdict_result,
    validate_panel_status,
    validate_post_message_status,
    validate_verdict_status,
)
from app.orchestration.schema.swarm.orchestration_swarm_board_schema import (
    AbortSwarmRunRequest,
    ConvergeSwarmRequest,
    CreateSwarmVerificationPanelRequest,
    PostSwarmMessageRequest,
    RecordSwarmVerdictRequest,
    SettleSwarmRequest,
    SwarmBoardMessagesFilter,
    SwarmStallCheckRequest,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling


class SwarmBoardMessageApplication:
    """Execute and validate message posting and page reads."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying this request's upstream authority.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def post_message(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: PostSwarmMessageRequest,
    ) -> OrchestrationOutcomeDto[PostSwarmMessageResponseDict]:
        """Post or exactly replay one board message.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            request: Strictly validated message command.
        Return:
            Source status and typed message response.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/messages",
            parse_result=partial(
                parse_post_message_result,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_message_id=request.message_id,
                expected_channel_id=request.channel_id,
                expected_author_member_id=request.author_member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
            validate_result_status=validate_post_message_status,
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def fetch_board_page(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        filters: SwarmBoardMessagesFilter,
    ) -> OrchestrationOutcomeDto[SwarmBoardPageResponseDict]:
        """Read one bounded source board page after an exact cursor.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            filters: Checked cursor, channel and page limit query.
        Return:
            Source status and ordered typed board page.
        """
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/messages",
            parse_result=partial(
                parse_board_page_result,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                filters=filters,
            ),
            params=filters.to_query_params(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result


class SwarmBoardVerificationApplication:
    """Execute source panel creation and verdict recording operations."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying this request's upstream authority.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def create_panel(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: CreateSwarmVerificationPanelRequest,
    ) -> OrchestrationOutcomeDto[SwarmVerificationPanelDict]:
        """Create or exactly replay one verification panel.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            request: Strictly validated panel command.
        Return:
            Source status and typed verification panel.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/panels",
            parse_result=partial(
                parse_panel_result,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_required_quorum=request.required_quorum,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
            validate_result_status=validate_panel_status,
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def record_verdict(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: RecordSwarmVerdictRequest,
    ) -> OrchestrationOutcomeDto[SwarmVerdictDict]:
        """Record or exactly replay one immutable verifier verdict.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            request: Strictly validated verdict command.
        Return:
            Source status and typed verifier verdict.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/verdicts",
            parse_result=partial(
                parse_verdict_result,
                expected_request_id=request.request_id,
                expected_swarm_run_id=swarm_run_id,
                expected_verifier_member_id=request.verifier_member_id,
                expected_panel_id=request.panel_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
            validate_result_status=validate_verdict_status,
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result


class SwarmBoardConvergenceApplication:
    """Execute convergence, settlement, abort and stall check operations."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying this request's upstream authority.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def converge(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: ConvergeSwarmRequest,
    ) -> OrchestrationOutcomeDto[ConvergeSwarmResponseDict]:
        """Record candidate digests and validate the source run echo.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            request: Strictly validated convergence command.
        Return:
            Source status and typed convergence response.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/converge",
            parse_result=partial(
                parse_convergence_result,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def settle(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: SettleSwarmRequest,
    ) -> OrchestrationOutcomeDto[ConvergeSwarmResponseDict]:
        """Settle a staged run and require the settled result.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            request: Strictly validated settlement command.
        Return:
            Source status and typed settled-run response.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/settle",
            parse_result=partial(
                parse_settlement_result,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def abort(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: AbortSwarmRunRequest,
    ) -> OrchestrationOutcomeDto[SwarmRunDict]:
        """Abort a run with the source-required empty JSON body.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            request: Empty validated abort request.
        Return:
            Source status and typed aborted run.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/abort",
            parse_result=partial(
                parse_abort_result,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def evaluate_stall(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: SwarmStallCheckRequest,
    ) -> OrchestrationOutcomeDto[SwarmStallCheckResponseDict]:
        """Evaluate caller-selected stall thresholds and validate the source report.

        Args:
            workspace_id: Workspace UUID selected by the public route.
            swarm_run_id: Swarm run UUID selected by the public route.
            request: Strictly validated stall check thresholds.
        Return:
            Source status and typed deterministic stall report.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/stall-check",
            parse_result=partial(
                parse_stall_check_result,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result
