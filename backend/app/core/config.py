

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "AI Support Agent"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Postgres ---
    postgres_user: str = "support_agent"
    postgres_password: str = "change_me"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "support_agent_db"
    database_url: str | None = None  # optional override

    # --- Qdrant ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "business_knowledge_base"
    qdrant_api_key: str | None = None

    # --- Auth (JWT) ---

    secret_key: str = "dev-secret-key-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours

    admin_email: str = "admin@serenitysalon.example"
    admin_password: str = "change_me_now"
    admin_seed_force_update: bool = False

    # --- Document upload / ingestion ---
    upload_dir: str = "app/uploads"
    max_upload_size_mb: int = 20
    allowed_upload_extensions: str = ".pdf,.docx,.doc"

    # --- Chunking ---
    chunk_size: int = 800  # characters
    chunk_overlap: int = 120  # characters

    # --- Embeddings ---

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    embedding_batch_size: int = 32

    # --- Retrieval ---
    retrieval_top_k: int = 5

    relevance_score_threshold: float = 0.35

    # --- LLM (Groq) ---
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    groq_temperature: float = 0.3
    groq_max_tokens: int = 600

    # --- Business identity (used in the system prompt) ---
    business_name: str = "AI Support Agent"
    business_description: str = "boutique hair, beauty, and wellness salon"

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
    def allowed_upload_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_upload_extensions.split(",") if ext.strip()]

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