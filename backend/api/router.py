from __future__ import annotations

from fastapi import APIRouter

from api.v1 import environments, experiments, scenarios


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(environments.router, tags=["environments"])
api_router.include_router(scenarios.router, tags=["scenarios"])
api_router.include_router(experiments.router, tags=["experiments"])
