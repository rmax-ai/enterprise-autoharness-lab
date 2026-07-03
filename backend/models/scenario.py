from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ScenarioCounts(BaseModel):
    train: int = 0
    validation: int = 0
    test: int = 0


class EnvironmentListItem(BaseModel):
    id: str
    name: str
    description: str
    action_count: int
    rule_count: int
    scenario_counts: ScenarioCounts
    status: Literal["ready", "missing-data"] = "ready"


class EnvironmentsResponse(BaseModel):
    environments: list[EnvironmentListItem]


class PolicyRuleView(BaseModel):
    rule_id: str
    description: str
    priority: int


class PolicyRulesResponse(BaseModel):
    environment: str
    rules: list[PolicyRuleView]


class ScenarioActor(BaseModel):
    user_id: str
    role: str
    approval_limit: float | int | None = None


class ScenarioPreview(BaseModel):
    scenario_id: str
    task: str
    actor: ScenarioActor
    max_steps: int
    tags: list[str]
    expense_count: int
    initial_state_preview: dict[str, object]
    initial_state: dict[str, object]


class ScenariosResponse(BaseModel):
    environment: str
    split: str
    count: int
    scenarios: list[ScenarioPreview]
