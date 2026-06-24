"""Application configuration.

All runtime configuration is loaded from environment variables (12-factor style)
via pydantic-settings. A single cached `Settings` instance is exposed through
`get_settings()`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- App ----
    app_name: str = "LearnGraph"
    environment: str = Field(default="development")

    # ---- LLM ----
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None
    # Name of a model entry defined in app/agents/models.yaml
    learngraph_default_model: str = Field(default="gpt-5")

    # ---- Supabase / DB ----
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    database_url: str | None = None

    # ---- Tools ----
    tavily_api_key: str | None = None
    youtube_api_key: str | None = None

    # ---- Observability ----
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "learngraph"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # ---- CORS ----
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_database(self) -> bool:
        return bool(self.database_url)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
