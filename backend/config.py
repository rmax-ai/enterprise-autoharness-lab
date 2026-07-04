from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    workspace_root: Path = REPO_ROOT
    api_title: str = "Enterprise AutoHarness Lab API"
    api_version: str = "0.1.0"
    cors_origins: list[str] = ["*"]


settings = Settings()
