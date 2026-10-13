from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the AI Complexity Analyzer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    app_version: str = "1.0.0"
    app_name: str = "AI Complexity Analyzer"

    # Input limits
    max_code_size_kb: int = 512

    # CORS
    allow_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    # AI Provider
    ai_provider: str = "mock"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: int = 30
    ai_max_retries: int = 2

    @property
    def max_code_size_bytes(self) -> int:
        return self.max_code_size_kb * 1024

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allow_origins.split(",") if o.strip()]

    @property
    def ai_provider_configured(self) -> bool:
        """True when a real AI provider key is present."""
        return bool(self.ai_api_key and self.ai_api_key not in {
            "", "your_openai_api_key_here", "CHANGE_ME"
        })


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
