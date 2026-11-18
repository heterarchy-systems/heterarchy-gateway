"""Parse and forward Native Swarm turn operations without domain decisions."""

from dataclasses import replace
from functools import partial
from uuid import UUID

from fastapi import status

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.swarm.swarm_turn_inner_dto import (
    ClaimSwarmWakeupCommandDto,
    CompleteSwarmTurnCommandDto,
    DispatchSwarmTurnCommandDto,
    FailSwarmTurnCommandDto,
    SwitchSwarmMemberModelCommandDto,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    SwarmMemberDict,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_turn_types import (
    DispatchSwarmTurnResponseDict,
    SwarmModelSwitchResponseDict,
    SwarmWakeupBatchDict,
)
from app.orchestration.application.orchestration_command_utils import (
    ORCHESTRATION_SWARM_EXCHANGE_POLICY,
    execute_orchestration_operation,
)
from app.orchestration.application.swarm.swarm_turn_parsers import (
    parse_claim_result,
    parse_dispatch_result,
    parse_member_result,
    parse_model_switch_result,
)
from app.orchestration.schema.swarm.orchestration_swarm_turn_schema import (
    ClaimSwarmWakeupRequest,
    CompleteSwarmTurnRequest,
    DispatchSwarmTurnRequest,
    FailSwarmTurnRequest,
    SwitchSwarmMemberModelRequest,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmTurnFailureDispositionEnum,
)
from app.shared.types.upstream_exchange import UpstreamExchangePolicy

_DISPATCH_SLACK_MS = 5_000
_MAX_DISPATCH_TIMEOUT_SECONDS = 900.0


def build_dispatch_exchange_policy(
    request: DispatchSwarmTurnRequest,
    timeout_floor_seconds: float,
) -> UpstreamExchangePolicy:
    """Build request-local bounds matching the Swarm dispatch transport.

    Args:
        request: Strictly validated dispatch request carrying the phase timeouts.
        timeout_floor_seconds: Runtime-configured baseline HTTP timeout.
    Return:
        Policy with Swarm byte caps and the source-compatible total deadline.
    """
    total_timeout_ms = (
        request.timeouts.startup_timeout_ms
        + request.timeouts.execution_timeout_ms
        + request.timeouts.termination_grace_ms
        + _DISPATCH_SLACK_MS
    )
    phase_timeout_seconds = total_timeout_ms / 1000.0
    timeout_seconds = min(
        max(timeout_floor_seconds, phase_timeout_seconds),
        _MAX_DISPATCH_TIMEOUT_SECONDS,
    )
    result = replace(ORCHESTRATION_SWARM_EXCHANGE_POLICY, timeout_seconds=timeout_seconds)
    return result


class SwarmTurnApplication:
    """Execute request-scoped Swarm turn calls and validate source readbacks."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Bind the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying request authority and transport.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def claim_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: ClaimSwarmWakeupRequest,
    ) -> OrchestrationOutcomeDto[SwarmWakeupBatchDict]:
        """Claim one member's coalesced wakeup batch.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible wakeup claim request.
        Return:
            Original HTTP status and typed wakeup result or backend error.
        """
        command = ClaimSwarmWakeupCommandDto(snapshot_id=request.snapshot_id)
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/claim",
            parse_result=partial(
                parse_claim_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
                snapshot_id=request.snapshot_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def complete_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: CompleteSwarmTurnRequest,
    ) -> OrchestrationOutcomeDto[SwarmMemberDict]:
        """Complete one member turn and commit its optional output receipt.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible completion request.
        Return:
            Original HTTP status and typed member result or backend error.
        """
        command = CompleteSwarmTurnCommandDto(
            expected_snapshot_id=request.expected_snapshot_id,
            output_commit_oid=request.output_commit_oid,
            output_tree_blake3_hex=request.output_tree_blake3_hex,
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/complete",
            parse_result=partial(
                parse_member_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def fail_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: FailSwarmTurnRequest,
    ) -> OrchestrationOutcomeDto[SwarmMemberDict]:
        """Release one failed or suspended turn using the source disposition.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible failure request.
        Return:
            Original HTTP status and typed member result or backend error.
        """
        command = FailSwarmTurnCommandDto(
            expected_snapshot_id=request.expected_snapshot_id,
            disposition=SwarmTurnFailureDispositionEnum(request.disposition),
            consume_turn=request.consume_turn,
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/fail",
            parse_result=partial(
                parse_member_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def dispatch_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: DispatchSwarmTurnRequest,
        timeout_floor_seconds: float,
    ) -> OrchestrationOutcomeDto[DispatchSwarmTurnResponseDict]:
        """Dispatch one member turn under the request-local phase deadline.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible dispatch request.
            timeout_floor_seconds: Runtime-configured HTTP timeout baseline.
        Return:
            Original HTTP status and typed dispatch result or backend error.
        """
        command = DispatchSwarmTurnCommandDto(
            snapshot_request_id=request.snapshot_request_id,
            snapshot_id=request.snapshot_id,
            activity_id=request.activity_id,
            default_worktree_path=request.default_worktree_path,
            lease_id=request.lease_id,
            lease_revision=request.lease_revision,
            lease_expires_at_ms=request.lease_expires_at_ms,
            mcp_grant=request.mcp_grant.to_inner_dto() if request.mcp_grant is not None else None,
            permissions=request.permissions.to_inner_dto(),
            timeouts=request.timeouts.to_inner_dto(),
            dispatched_at_ms=request.dispatched_at_ms,
            clean_exit_output_commit_oid=request.clean_exit_output_commit_oid,
            clean_exit_output_tree_blake3_hex=request.clean_exit_output_tree_blake3_hex,
            forge_session_id=request.forge_session_id,
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/dispatch",
            parse_result=partial(
                parse_dispatch_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
                snapshot_id=request.snapshot_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=build_dispatch_exchange_policy(
                request=request, timeout_floor_seconds=timeout_floor_seconds
            ),
        )
        return result

    async def switch_member_model(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: SwitchSwarmMemberModelRequest,
    ) -> OrchestrationOutcomeDto[SwarmModelSwitchResponseDict]:
        """Switch one quota-suspended member to a source-supported Profile target.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible model-switch request.
        Return:
            Original HTTP status and typed model-switch result or backend error.
        """
        command = SwitchSwarmMemberModelCommandDto(
            new_profile_id=request.new_profile_id,
            request_id=request.request_id,
            profile_id=request.profile_id,
            expected_profile_revision=request.expected_profile_revision,
            new_preference=(
                request.new_preference.to_inner_dto()
                if request.new_preference is not None
                else None
            ),
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/model-switch",
            parse_result=partial(
                parse_model_switch_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result
