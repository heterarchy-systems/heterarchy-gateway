"""Compose the public Forge routes behind one prefix and bearer policy."""

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Security
from fastapi.security import HTTPBearer

from app.forge.routers.dag.forge_dag_routers import router as dag_router
from app.forge.routers.swarm.forge_swarm_routers import router as swarm_router
from app.forge.routers.workspace.forge_workspace_routers import router as workspace_router

router = APIRouter(
    prefix="/forges",
    tags=["forge"],
    route_class=DishkaRoute,
    dependencies=[Security(HTTPBearer(auto_error=False, scheme_name="ForgeBearer"))],
)
router.include_router(workspace_router)
router.include_router(dag_router)
router.include_router(swarm_router)
