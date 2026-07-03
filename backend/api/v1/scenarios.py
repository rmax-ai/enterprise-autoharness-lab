from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from config import settings
from models import ScenariosResponse, ScenarioPreview
from services.file_reader import read_jsonl


router = APIRouter()

SPLIT_ALIASES = {
    "train": "train",
    "val": "validation",
    "validation": "validation",
    "test": "test",
}


def _build_preview(initial_state: dict[str, object]) -> dict[str, object]:
    expenses = initial_state.get("expenses", {})
    if not isinstance(expenses, dict):
        return {"expenses": {}}

    preview_items = {}
    for expense_id, expense in list(expenses.items())[:2]:
        if isinstance(expense, dict):
            preview_items[expense_id] = {
                key: expense.get(key)
                for key in ("amount", "state", "submitter", "currency")
                if key in expense
            }
    return {"expenses": preview_items}


@router.get("/scenarios/{env_id}", response_model=ScenariosResponse)
async def get_scenarios(
    env_id: str,
    split: str = Query("train", pattern="^(train|val|validation|test)$"),
) -> ScenariosResponse:
    canonical_split = SPLIT_ALIASES[split]
    path = settings.workspace_root / "scenarios" / env_id / f"{canonical_split}.jsonl"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown scenario split: {env_id}/{split}")

    rows = await read_jsonl(path)
    scenarios = []
    for row in rows:
        initial_state = row.get("initial_state", {})
        expense_count = 0
        if isinstance(initial_state, dict):
            expenses = initial_state.get("expenses", {})
            if isinstance(expenses, dict):
                expense_count = len(expenses)
        scenarios.append(
            ScenarioPreview(
                scenario_id=str(row.get("scenario_id", "")),
                task=str(row.get("task", "")),
                actor=row.get("actor", {}),
                max_steps=int(row.get("max_steps", 0)),
                tags=list(row.get("tags", [])),
                expense_count=expense_count,
                initial_state_preview=_build_preview(initial_state if isinstance(initial_state, dict) else {}),
                initial_state=initial_state if isinstance(initial_state, dict) else {},
            )
        )

    return ScenariosResponse(
        environment=env_id,
        split=canonical_split,
        count=len(scenarios),
        scenarios=scenarios,
    )
