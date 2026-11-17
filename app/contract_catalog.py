"""Concrete public response contracts bound by the Gateway composition root."""

from pydantic import BaseModel

from app.forge.schema.activity.forge_activity_schema import ForgeActivityListResponse
from app.forge.schema.dag.forge_dag_schema import (
    ForgeDagReadCurrentResponse,
    ForgeDagSettleResponse,
)
from app.forge.schema.location.forge_location_schema import ForgeLocationListResponse
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberCaptureResponse,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
    ForgeSwarmConvergeResponse,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmMaterializeHybridResponse,
    ForgeSwarmSettlementGetResponse,
    ForgeSwarmSettleResponse,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeResponse,
    ForgeSwarmWorkspaceGetResponse,
    ForgeSwarmWorkspaceProvisionResponse,
)
from app.forge.schema.workspace.forge_workspace_schema import ForgeWorkspaceListResponse
from app.mixed_module.schema.mixed_dag_governance_schema import MixedDagGovernanceResponse
from app.mixed_module.schema.mixed_swarm_overview_schema import MixedSwarmOverviewResponse
from app.orchestration.schema.autonomy.orchestration_autonomy_reviewer_schema import (
    ReviewerOperationResponse,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_scope_schema import (
    RegisteredWorkspaceScopeResponse,
    WorkspaceScopeListResponse,
    WorkspaceScopeQueryResponse,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_settlement_schema import (
    DagSettlementAuthorityResponse,
    DagSettlementGovernanceResponse,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_snapshot_schema import (
    ExecutionSnapshotOutcomeResponse,
    ExecutionSnapshotQueryResponse,
)
from app.orchestration.schema.forge_bridge.orchestration_forge_bridge_schema import (
    ForgeConvergeSwarmResponse,
    ForgeSettleSwarmResponse,
    SyncAutonomyOutboxResponse,
)
from app.orchestration.schema.profile.orchestration_profile_schema import (
    ProfileCreateResponse,
    ProfileListResponse,
    ProfileMutationResponse,
    ProfileResponse,
)
from app.orchestration.schema.realtime.orchestration_realtime_event_schema import (
    OrchestrationRealtimeData,
)
from app.orchestration.schema.swarm.orchestration_swarm_board_schema import (
    ConvergeSwarmResponse,
    PostSwarmMessageResponse,
    SwarmBoardPageResponse,
    SwarmStallCheckResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_run_schema import (
    CreateSwarmRunResponse,
    KillSwarmMemberResponse,
    SubscribeSwarmChannelResponse,
    SwarmRunInspectionResponse,
    SwarmRunListResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import (
    SwarmChannelSchema,
    SwarmMemberSchema,
    SwarmRunSchema,
    SwarmVerdictSchema,
    SwarmVerificationPanelSchema,
)
from app.orchestration.schema.swarm.orchestration_swarm_turn_schema import (
    DispatchSwarmTurnResponse,
    SwarmModelSwitchResponse,
    SwarmWakeupBatchResponse,
)
from app.shared.ingredient_element.gateway.request_trace_enums import ContractName


def create_contract_catalog() -> dict[ContractName, type[BaseModel]]:
    """Bind operation identities to their concrete public response schemas.

    Args:
        None.
    Return:
        The current response-contract catalog for diagnostics.
    """
    result: dict[ContractName, type[BaseModel]] = {
        ContractName.FORGE_LOCATION_LIST: ForgeLocationListResponse,
        ContractName.FORGE_WORKSPACE_LIST: ForgeWorkspaceListResponse,
        ContractName.FORGE_ACTIVITY_LIST: ForgeActivityListResponse,
        ContractName.FORGE_DAG_READ_CURRENT: ForgeDagReadCurrentResponse,
        ContractName.FORGE_DAG_SETTLE: ForgeDagSettleResponse,
        ContractName.FORGE_SWARM_WORKSPACE_PROVISION: ForgeSwarmWorkspaceProvisionResponse,
        ContractName.FORGE_SWARM_WORKSPACE_GET: ForgeSwarmWorkspaceGetResponse,
        ContractName.FORGE_SWARM_MEMBER_CAPTURE: ForgeSwarmMemberCaptureResponse,
        ContractName.FORGE_SWARM_CONVERGE: ForgeSwarmConvergeResponse,
        ContractName.FORGE_SWARM_SETTLE: ForgeSwarmSettleResponse,
        ContractName.FORGE_SWARM_MATERIALIZE_HYBRID: ForgeSwarmMaterializeHybridResponse,
        ContractName.FORGE_SWARM_SETTLEMENT_GET: ForgeSwarmSettlementGetResponse,
        ContractName.FORGE_SWARM_PURGE: ForgeSwarmPurgeResponse,
        ContractName.ORCHESTRATION_PROFILE_CREATE: ProfileCreateResponse,
        ContractName.ORCHESTRATION_PROFILE_LIST: ProfileListResponse,
        ContractName.ORCHESTRATION_PROFILE_GET: ProfileResponse,
        ContractName.ORCHESTRATION_PROFILE_UPDATE: ProfileMutationResponse,
        ContractName.ORCHESTRATION_PROFILE_DISABLE: ProfileMutationResponse,
        ContractName.ORCHESTRATION_PROFILE_RETIRE: ProfileMutationResponse,
        ContractName.ORCHESTRATION_WORKSPACE_SCOPE_LIST: WorkspaceScopeListResponse,
        ContractName.ORCHESTRATION_WORKSPACE_SCOPE_REGISTER: RegisteredWorkspaceScopeResponse,
        ContractName.ORCHESTRATION_WORKSPACE_SCOPE_GET: WorkspaceScopeQueryResponse,
        ContractName.ORCHESTRATION_REVIEWER_ASSIGN: ReviewerOperationResponse,
        ContractName.ORCHESTRATION_REVIEWER_VERDICT: ReviewerOperationResponse,
        ContractName.ORCHESTRATION_NODE_COMPLETION_GATE: ReviewerOperationResponse,
        ContractName.ORCHESTRATION_EXECUTION_SNAPSHOT_PREPARE: ExecutionSnapshotOutcomeResponse,
        ContractName.ORCHESTRATION_EXECUTION_SNAPSHOT_GET: ExecutionSnapshotQueryResponse,
        ContractName.ORCHESTRATION_DAG_SETTLEMENT_AUTHORITY: DagSettlementAuthorityResponse,
        ContractName.ORCHESTRATION_DAG_SETTLEMENT_GOVERNANCE: DagSettlementGovernanceResponse,
        ContractName.ORCHESTRATION_SWARM_CREATE: CreateSwarmRunResponse,
        ContractName.ORCHESTRATION_SWARM_LIST: SwarmRunListResponse,
        ContractName.ORCHESTRATION_SWARM_GET: SwarmRunInspectionResponse,
        ContractName.ORCHESTRATION_SWARM_CHANNEL_CREATE: SwarmChannelSchema,
        ContractName.ORCHESTRATION_SWARM_CHANNEL_SUBSCRIBE: SubscribeSwarmChannelResponse,
        ContractName.ORCHESTRATION_SWARM_MEMBER_ADD: SwarmMemberSchema,
        ContractName.ORCHESTRATION_SWARM_MEMBER_KILL: KillSwarmMemberResponse,
        ContractName.ORCHESTRATION_SWARM_TURN_CLAIM: SwarmWakeupBatchResponse,
        ContractName.ORCHESTRATION_SWARM_TURN_COMPLETE: SwarmMemberSchema,
        ContractName.ORCHESTRATION_SWARM_TURN_FAIL: SwarmMemberSchema,
        ContractName.ORCHESTRATION_SWARM_TURN_DISPATCH: DispatchSwarmTurnResponse,
        ContractName.ORCHESTRATION_SWARM_MEMBER_MODEL_SWITCH: SwarmModelSwitchResponse,
        ContractName.ORCHESTRATION_SWARM_MESSAGE_POST: PostSwarmMessageResponse,
        ContractName.ORCHESTRATION_SWARM_MESSAGE_LIST: SwarmBoardPageResponse,
        ContractName.ORCHESTRATION_SWARM_PANEL_CREATE: SwarmVerificationPanelSchema,
        ContractName.ORCHESTRATION_SWARM_VERDICT_RECORD: SwarmVerdictSchema,
        ContractName.ORCHESTRATION_SWARM_CONVERGE: ConvergeSwarmResponse,
        ContractName.ORCHESTRATION_SWARM_SETTLE: ConvergeSwarmResponse,
        ContractName.ORCHESTRATION_SWARM_ABORT: SwarmRunSchema,
        ContractName.ORCHESTRATION_SWARM_STALL_CHECK: SwarmStallCheckResponse,
        ContractName.MIXED_SWARM_OVERVIEW: MixedSwarmOverviewResponse,
        ContractName.MIXED_DAG_GOVERNANCE: MixedDagGovernanceResponse,
        ContractName.ORCHESTRATION_SWARM_FORGE_CONVERGE: ForgeConvergeSwarmResponse,
        ContractName.ORCHESTRATION_SWARM_FORGE_SETTLE: ForgeSettleSwarmResponse,
        ContractName.ORCHESTRATION_AUTONOMY_OUTBOX_SYNC: SyncAutonomyOutboxResponse,
        ContractName.ORCHESTRATION_EVENTS: OrchestrationRealtimeData,
    }
    return result
