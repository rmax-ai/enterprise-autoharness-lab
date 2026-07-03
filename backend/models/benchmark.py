from __future__ import annotations

from pydantic import BaseModel


class ExperimentMetrics(BaseModel):
    task_success_rate: float
    invalid_action_rate: float
    policy_denial_rate: float | None = None
    runtime_error_rate: float | None = None
    false_rejection_rate: float | None = None
    false_acceptance_rate: float | None = None
    composite_score: float
    total_actions: int


class ExperimentListItem(BaseModel):
    experiment_id: str
    environment: str
    agent: str
    timestamp: str
    metrics: ExperimentMetrics


class ExperimentDetail(ExperimentListItem):
    source_file: str


class ExperimentsResponse(BaseModel):
    experiments: list[ExperimentListItem]
