from __future__ import annotations

import sys
from pathlib import Path

from pydantic.v1 import BaseSettings, Field


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class Settings(BaseSettings):
    workspace_root: Path = Field(default=REPO_ROOT, env="WORKSPACE_ROOT")
    api_title: str = "Enterprise AutoHarness Lab API"
    api_version: str = "0.1.0"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    class Config:
        case_sensitive = False


settings = Settings()
