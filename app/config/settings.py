"""Central application configuration.

All configuration is loaded from environment variables (see .env.example).
Nothing secret is ever hardcoded here — this module only defines defaults
and validation for values that MUST come from the environment in production.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")

    # --- Database ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/coursework_checker.db",
        alias="DATABASE_URL",
    )

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # --- LLM ---
    llm_provider: Literal["mock", "openai"] = Field(default="mock", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_max_output_tokens: int = Field(default=2000, alias="LLM_MAX_OUTPUT_TOKENS")
    llm_timeout_seconds: int = Field(default=60, alias="LLM_TIMEOUT_SECONDS")
    llm_analysis_timeout_seconds: int = Field(default=600, alias="LLM_ANALYSIS_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")

    # --- Limits ---
    max_file_size_mb: int = Field(default=20, alias="MAX_FILE_SIZE_MB")
    max_pages: int = Field(default=100, alias="MAX_PAGES")
    max_ai_tokens_per_check: int = Field(default=60000, alias="MAX_AI_TOKENS_PER_CHECK")
    max_checks_per_day: int = Field(default=20, alias="MAX_CHECKS_PER_DAY")
    file_retention_hours: int = Field(default=24, alias="FILE_RETENTION_HOURS")
    report_retention_hours: int = Field(default=168, alias="REPORT_RETENTION_HOURS")
    result_retention_days: int = Field(default=30, alias="RESULT_RETENTION_DAYS")
    max_active_checks: int = Field(default=2, alias="MAX_ACTIVE_CHECKS")
    max_archive_parts: int = Field(default=2000, alias="MAX_ARCHIVE_PARTS")
    max_uncompressed_mb: int = Field(default=100, alias="MAX_UNCOMPRESSED_MB")
    max_archive_part_mb: int = Field(default=32, alias="MAX_ARCHIVE_PART_MB")
    max_compression_ratio: int = Field(default=200, alias="MAX_COMPRESSION_RATIO")
    job_timeout_seconds: int = Field(default=900, alias="JOB_TIMEOUT_SECONDS")
    worker_max_jobs: int = Field(default=2, alias="WORKER_MAX_JOBS")
    max_job_attempts: int = Field(default=3, alias="MAX_JOB_ATTEMPTS")
    # Operator-issued bearer tokens mapped to Telegram user IDs. Empty disables access.
    api_tokens: dict[str, int] = Field(default_factory=dict, alias="API_TOKENS")

    # --- Storage ---
    storage_dir: Path = Field(default=Path("./data/storage"), alias="STORAGE_DIR")
    reports_dir: Path = Field(default=Path("./data/reports"), alias="REPORTS_DIR")

    # --- App ---
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_rule_preset: str = Field(default="makhambet_coursework", alias="DEFAULT_RULE_PRESET")

    # Top-level `rules/` (NOT `app/rules/`) is the admin-editable preset
    # directory: adding a .yaml here creates a new RulePreset with zero
    # Python code changes (spec §10/§23).
    presets_dir: Path = Path(__file__).resolve().parent.parent.parent / "rules" / "presets"
    prompts_dir: Path = Path(__file__).resolve().parent.parent.parent / "prompts"

    @field_validator(
        "llm_max_output_tokens",
        "llm_timeout_seconds",
        "llm_analysis_timeout_seconds",
        "llm_max_retries",
        "max_file_size_mb",
        "max_pages",
        "max_ai_tokens_per_check",
        "max_checks_per_day",
        "file_retention_hours",
        "report_retention_hours",
        "result_retention_days",
        "max_active_checks",
        "max_archive_parts",
        "max_uncompressed_mb",
        "max_archive_part_mb",
        "max_compression_ratio",
        "job_timeout_seconds",
        "worker_max_jobs",
        "max_job_attempts",
    )
    @classmethod
    def _positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @field_validator("storage_dir", "reports_dir")
    @classmethod
    def _ensure_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("api_tokens")
    @classmethod
    def _valid_api_tokens(cls, value: dict[str, int]) -> dict[str, int]:
        if any(len(token) < 32 or user_id <= 0 for token, user_id in value.items()):
            raise ValueError("API tokens require at least 32 characters and positive user IDs")
        return value

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x) for x in self.admin_ids.split(",") if x.strip().isdigit()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
