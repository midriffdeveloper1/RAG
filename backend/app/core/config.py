from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- App ---
    app_name: str = "AI Support Agent"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

  
    cors_origins: str = "http://localhost:5173,http://localhost:3000"


    postgres_user: str = "support_agent"
    postgres_password: str = "change_me"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "support_agent_db"
    database_url: str | None = None  # optional override


    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "business_knowledge_base"
    qdrant_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Build the Postgres connection string, unless DATABASE_URL is set explicitly."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import and call this, don't instantiate Settings() directly."""
    return Settings()
