"""Pure request forwarding and normalization for Agent Profile contracts."""

from functools import partial
from uuid import UUID

from fastapi import status

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.profile_inner_dto import (
    CreateProfileCommandDto,
    ProfileLifecycleCommandDto,
    UpdateProfileConfigCommandDto,
)
from app.orchestration.application.inner_dto.types.profile_types import (
    ProfileCreateOutcomeDict,
    ProfileDict,
    ProfileMutationDict,
)
from app.orchestration.application.orchestration_command_utils import (
    execute_orchestration_operation,
)
from app.orchestration.application.profile_parsers import (
    parse_profile_create_result,
    parse_profile_lifecycle_result,
    parse_profile_list_result,
    parse_profile_result,
    parse_profile_update_result,
    profile_configuration_from_request,
)
from app.orchestration.schema.profile.orchestration_profile_schema import (
    CreateProfileRequest,
    ProfileLifecycleRequest,
    ProfileListFilter,
    UpdateProfileConfigRequest,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.ingredient_element.orchestration.profile_enums import (
    ProfileLifecycleStateEnum,
    ProfileMutationKindEnum,
)

_PROFILE_LIFECYCLE_TARGETS = {
    ProfileMutationKindEnum.DISABLE: ProfileLifecycleStateEnum.DISABLED,
    ProfileMutationKindEnum.RETIRE: ProfileLifecycleStateEnum.RETIRED,
}


class ProfileApplication:
    """Forward Profile operations and parse source-owned JSON contracts."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the application with the request-scoped caller.

        Args:
            orchestration_calling: Request-scoped Orchestration transport.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def create_profile(
        self,
        request: CreateProfileRequest,
    ) -> OrchestrationOutcomeDto[ProfileCreateOutcomeDict]:
        """Create or exactly replay one Profile request.

        Args:
            request: Validated Profile create contract.
        Return:
            Source status with the typed Profile create outcome.
        """
        command: CreateProfileCommandDto = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path="/internal/v1/agent-profiles",
            parse_result=partial(
                parse_profile_create_result,
                expected_request_id=request.request_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
        )
        return result

    async def fetch_profiles(
        self,
        filters: ProfileListFilter,
    ) -> OrchestrationOutcomeDto[list[ProfileDict]]:
        """Fetch the bounded root-array Profile catalogue.

        Args:
            filters: Optional source limit query.
        Return:
            Source status with typed Profile result dictionaries.
        """
        result_limit = filters.limit or 64
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path="/internal/v1/agent-profiles",
            parse_result=partial(parse_profile_list_result, result_limit=result_limit),
            params=filters.to_query_params(),
        )
        return result

    async def fetch_profile(
        self,
        profile_id: UUID,
    ) -> OrchestrationOutcomeDto[ProfileDict]:
        """Fetch one Profile and require its source identity echo.

        Args:
            profile_id: Profile UUID from the route path.
        Return:
            Source status with the typed Profile result.
        """
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path=f"/internal/v1/agent-profiles/{profile_id}",
            parse_result=partial(parse_profile_result, expected_profile_id=profile_id),
        )
        return result

    async def update_profile_config(
        self,
        profile_id: UUID,
        request: UpdateProfileConfigRequest,
    ) -> OrchestrationOutcomeDto[ProfileMutationDict]:
        """Update mutable Profile configuration at an expected revision.

        Args:
            profile_id: Profile UUID from the route path.
            request: Validated configuration update.
        Return:
            Source status with the typed mutation receipt.
        """
        command: UpdateProfileConfigCommandDto = request.to_inner_dto()
        expected_configuration = profile_configuration_from_request(command=command)
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="PUT",
            path=f"/internal/v1/agent-profiles/{profile_id}/configuration",
            parse_result=partial(
                parse_profile_update_result,
                expected_request_id=request.request_id,
                expected_profile_id=profile_id,
                expected_revision=request.expected_revision,
                expected_configuration=expected_configuration,
            ),
            body=command.to_dict(),
        )
        return result

    async def disable_profile(
        self,
        profile_id: UUID,
        request: ProfileLifecycleRequest,
    ) -> OrchestrationOutcomeDto[ProfileMutationDict]:
        """Disable one Profile at an expected revision.

        Args:
            profile_id: Profile UUID from the route path.
            request: Validated lifecycle mutation request.
        Return:
            Source status with the typed mutation receipt.
        """
        result = await _execute_lifecycle_profile(
            calling=self._orchestration_calling,
            profile_id=profile_id,
            request=request,
            kind=ProfileMutationKindEnum.DISABLE,
        )
        return result

    async def retire_profile(
        self,
        profile_id: UUID,
        request: ProfileLifecycleRequest,
    ) -> OrchestrationOutcomeDto[ProfileMutationDict]:
        """Retire one Profile at an expected revision.

        Args:
            profile_id: Profile UUID from the route path.
            request: Validated lifecycle mutation request.
        Return:
            Source status with the typed mutation receipt.
        """
        result = await _execute_lifecycle_profile(
            calling=self._orchestration_calling,
            profile_id=profile_id,
            request=request,
            kind=ProfileMutationKindEnum.RETIRE,
        )
        return result


async def _execute_lifecycle_profile(
    calling: OrchestrationCalling,
    profile_id: UUID,
    request: ProfileLifecycleRequest,
    kind: ProfileMutationKindEnum,
) -> OrchestrationOutcomeDto[ProfileMutationDict]:
    """Forward one lifecycle command and validate its identity receipt.

    Args:
        calling: Request-scoped Orchestration caller.
        profile_id: Profile UUID from the route path.
        request: Validated lifecycle mutation request.
        kind: Source mutation kind matching the route.
    Return:
        Source status with the typed mutation receipt.
    """
    command: ProfileLifecycleCommandDto = request.to_inner_dto()
    target_state = _PROFILE_LIFECYCLE_TARGETS[kind]
    result = await execute_orchestration_operation(
        calling=calling,
        method="POST",
        path=f"/internal/v1/agent-profiles/{profile_id}/{kind.value}",
        parse_result=partial(
            parse_profile_lifecycle_result,
            expected_request_id=request.request_id,
            expected_profile_id=profile_id,
            expected_revision=request.expected_revision,
            expected_kind=kind,
            expected_state=target_state,
        ),
        body=command.to_dict(),
    )
    return result
