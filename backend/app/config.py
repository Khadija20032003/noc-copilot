"""Settings from environment variables (and a .env file at the repo root or in backend/)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-haiku-5-5"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env"), extra="ignore"
    )

    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_temperature: float = 0.0

    kb_dir: Path = REPO_ROOT / "knowledge_base"
    db_path: Path = REPO_ROOT / "data" / "nordtel.db"
    tickets_path: Path = REPO_ROOT / "data" / "tickets.json"

    max_steps: int = 8        # supervisor decisions per question, guards against loops
    max_revisions: int = 2    # verifier revision rounds before answering with a caveat
    max_tool_iterations: int = 6  # tool-calling rounds per agent invocation

    @property
    def model_name(self) -> str:
        return self.llm_model or DEFAULT_MODELS[self.llm_provider]

    @property
    def api_key(self) -> str:
        return self.openai_api_key if self.llm_provider == "openai" else self.anthropic_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
