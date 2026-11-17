"""Compose the Orchestration schema-factory HTTP surface."""

from fastapi import APIRouter, Security
from fastapi.security import HTTPBearer

from app.orchestration.routers.autonomy.orchestration_autonomy_routers import (
    router as autonomy_router,
)
from app.orchestration.routers.forge_bridge.orchestration_forge_bridge_routers import (
    router as forge_bridge_router,
)
from app.orchestration.routers.profile.orchestration_profile_routers import router as profile_router
from app.orchestration.routers.realtime.orchestration_realtime_routers import (
    router as realtime_router,
)
from app.orchestration.routers.swarm.orchestration_swarm_board_routers import (
    router as swarm_board_router,
)
from app.orchestration.routers.swarm.orchestration_swarm_run_routers import (
    router as swarm_run_router,
)
from app.orchestration.routers.swarm.orchestration_swarm_turn_routers import (
    router as swarm_turn_router,
)

router = APIRouter(
    prefix="/orchestrations",
    tags=["orchestration"],
    dependencies=[Security(HTTPBearer(auto_error=False, scheme_name="OrchestrationBearer"))],
)
router.include_router(profile_router)
router.include_router(autonomy_router)
router.include_router(swarm_run_router)
router.include_router(swarm_turn_router)
router.include_router(swarm_board_router)

router.include_router(forge_bridge_router)
router.include_router(realtime_router)
