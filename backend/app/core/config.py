from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "Smart Expense Tracker API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_expense_tracker"
    jwt_secret_key: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    rag_top_k: int = 5
    automation_api_key: str | None = None
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"false", "0", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url_driver(cls, value):
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if normalized.startswith("postgres://"):
            return "postgresql+psycopg://" + normalized[len("postgres://"):]
        if normalized.startswith("postgresql://") and "+" not in normalized.split("://", 1)[0]:
            return "postgresql+psycopg://" + normalized[len("postgresql://"):]

        return normalized

    def get_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
