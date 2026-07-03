from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config import settings
from models import EnvironmentsResponse, EnvironmentListItem, PolicyRulesResponse
from services.file_reader import discover_environments, load_policy_rules


router = APIRouter()


@router.get("/environments", response_model=EnvironmentsResponse)
async def get_environments() -> EnvironmentsResponse:
    environment_rows = discover_environments(settings.workspace_root)
    environments = []
    for row in environment_rows:
        rules = load_policy_rules(settings.workspace_root, str(row["id"]))
        environments.append(EnvironmentListItem(**row, rule_count=len(rules)))
    return EnvironmentsResponse(environments=environments)


@router.get("/environments/{env_id}/policies", response_model=PolicyRulesResponse)
async def get_environment_policies(env_id: str) -> PolicyRulesResponse:
    rules = load_policy_rules(settings.workspace_root, env_id)
    if not rules:
        raise HTTPException(status_code=404, detail=f"Unknown environment: {env_id}")
    return PolicyRulesResponse(environment=env_id, rules=rules)
