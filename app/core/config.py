from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = Field(..., min_length=1)

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_collection_name: str = Field(default="policyguard_docs")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379")

    # App
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Costs
    cost_embedding_per_m: float = Field(default=0.02, gt=0)
    cost_input_per_m: float = Field(default=0.50, gt=0)
    cost_output_per_m: float = Field(default=1.50, gt=0)

    # Security
    employee_api_key: str = Field(...)
    manager_api_key: str = Field(...)
    admin_api_key: str = Field(...)

    secret_key: str = Field(...)
    api_auth_enabled: bool = Field(default=True)
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def valid_api_keys(self) -> dict[str, str]:
        return {
            self.employee_api_key: "employee",
            self.manager_api_key: "manager",
            self.admin_api_key: "admin",
        }

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        v = v.strip()

        if not v.startswith(("sk-", "sk-proj-")):
            raise ValueError(
                "Invalid OpenAI API key format"
            )

        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "production", "staging"}

        v = v.lower()

        if v not in allowed:
            raise ValueError(
                f"environment must be one of {allowed}"
            )

        return v


settings = Settings()