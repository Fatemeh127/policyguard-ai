"""Application configuration settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    # OpenAI
    openai_api_key: str = Field(..., min_length=1)

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection_name: str = Field(default="policyguard_docs", min_length=1)
    embedding_dim: int = Field(default=1536, gt=0)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379")

    # Chat session
    CHAT_TTL = 60 * 60 * 24
    MAX_MESSAGES = 50

    # App
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    debug: bool = False
    log_file: str | None = None

    # CORS
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8501", "http://127.0.0.1:8501"]
    )

    # Costs per 1M tokens
    cost_embedding_per_m: float = Field(default=0.02, gt=0)
    cost_input_per_m: float = Field(default=0.50, gt=0)
    cost_output_per_m: float = Field(default=1.50, gt=0)

    # OpenAI model config
    openai_chat_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    openai_max_tokens: int = Field(default=500, gt=0)
    openai_timeout_seconds: float = Field(default=30.0, gt=0)
    openai_max_retries: int = Field(default=2, ge=0)

    # Retrieval
    min_retrieval_score: float = Field(default=0.5, ge=0.0, le=1.0)

    # Security
    employee_api_key: str = Field(..., min_length=16)
    manager_api_key: str = Field(..., min_length=16)
    admin_api_key: str = Field(..., min_length=16)
    secret_key: str = Field(..., min_length=32)
    api_auth_enabled: bool = True

    # JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=1440, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    # Logging
    noisy_loggers: list[str] = Field(
        default_factory=lambda: [
            "httpx",
            "urllib3",
            "asyncio",
            "multipart",
            "uvicorn.access",
        ]
    )

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_strategy: str = "fixed-window"

    # Safety
    fail_open_moderation: bool = True

    # Chunking
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0, lt=1000)
    sample_docs_dir: Path = Path("data/sample_docs")

    @model_validator(mode="after")
    def validate_chunking(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("OpenAI API key cannot be empty")

        if not value.startswith(("sk-", "sk-proj-")):
            raise ValueError("Invalid OpenAI API key format")

        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        if not value.startswith("redis://"):
            raise ValueError("redis_url must start with redis://")
        return value

    @field_validator("qdrant_url")
    @classmethod
    def validate_qdrant_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("qdrant_url must start with http:// or https://")
        return value.rstrip("/")

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("Wildcard CORS origin '*' is not allowed in production config")
        return value

    @property
    def api_key_role_map(self) -> dict[str, str]:
        """Map API keys to application roles."""
        return {
            self.employee_api_key: "employee",
            self.manager_api_key: "manager",
            self.admin_api_key: "admin",
        }


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = get_settings()
