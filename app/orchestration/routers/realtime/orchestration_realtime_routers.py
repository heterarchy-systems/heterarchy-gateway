"""Typed HTTP entry point for the Orchestration workspace SSE stream."""

from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, status
from fastapi.responses import StreamingResponse

from app.orchestration.exceptions.realtime_exceptions import REALTIME_RESPONSES
from app.orchestration.realtime.realtime_sse import (
    SendTimeoutStreamingResponse,
    open_realtime_stream,
)
from app.orchestration.schema.types.swarm_types import NonNilSwarmUUID
from app.shared.api_calling_box.orchestration_event_calling import (
    OrchestrationEventCalling,
)
from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeHeaderNameEnum,
)

router = APIRouter(prefix="/workspaces", route_class=DishkaRoute)


@router.get(
    "/{workspace_id}/events",
    response_class=SendTimeoutStreamingResponse,
    status_code=status.HTTP_200_OK,
    responses=REALTIME_RESPONSES,
)
async def workspace_realtime_events_route(
    workspace_id: NonNilSwarmUUID,
    calling: FromDishka[OrchestrationEventCalling],
    last_event_id: Annotated[
        str | None,
        Header(
            alias=RealtimeHeaderNameEnum.LAST_EVENT_ID.value,
            description="Source resume cursor epoch:sequence.",
        ),
    ] = None,
    session_id: Annotated[
        str | None,
        Header(
            alias=RealtimeHeaderNameEnum.SESSION_ID.value,
            description="Optional source workspace-read session selector.",
        ),
    ] = None,
) -> StreamingResponse:
    """Stream scoped Orchestration events with typed admission failures.

    Args:
        workspace_id: Workspace scope selected by the public route.
        calling: Request-owned caller carrying Orchestration authorization.
        last_event_id: Optional cursor forwarded to the source unchanged.
        session_id: Optional workspace-read selector forwarded to the source.
    Return:
        Streaming response that owns source cancellation and cleanup.
    """
    result = await open_realtime_stream(
        calling=calling,
        workspace_id=workspace_id,
        last_event_id=last_event_id,
        session_id=session_id,
    )
    return result
