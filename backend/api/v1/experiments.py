from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings
from models import ExperimentDetail, ExperimentListItem, ExperimentsResponse
from services.file_reader import read_json


router = APIRouter()


def _benchmark_files(root: Path) -> list[Path]:
    return sorted((root / "docs" / "benchmarks").glob("*-test-*.json"))


def _experiment_metadata(path: Path) -> dict[str, str]:
    stem_parts = path.stem.split("-")
    if len(stem_parts) < 4:
        raise ValueError(f"Unexpected benchmark filename: {path.name}")

    agent = stem_parts[-1]
    environment = "-".join(stem_parts[:-2])
    timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).replace(microsecond=0)
    return {
        "experiment_id": f"{agent}-test",
        "environment": environment,
        "agent": agent,
        "timestamp": timestamp.isoformat().replace("+00:00", ""),
    }


@router.get("/experiments", response_model=ExperimentsResponse)
async def get_experiments() -> ExperimentsResponse:
    experiments = []
    for path in _benchmark_files(settings.workspace_root):
        metadata = _experiment_metadata(path)
        payload = await read_json(path)
        experiments.append(ExperimentListItem(**metadata, metrics=payload))
    experiments.sort(key=lambda item: item.timestamp, reverse=True)
    return ExperimentsResponse(experiments=experiments)


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(experiment_id: str) -> ExperimentDetail:
    for path in _benchmark_files(settings.workspace_root):
        metadata = _experiment_metadata(path)
        if metadata["experiment_id"] != experiment_id:
            continue
        payload = await read_json(path)
        return ExperimentDetail(**metadata, metrics=payload, source_file=path.name)
    raise HTTPException(status_code=404, detail=f"Unknown experiment: {experiment_id}")
