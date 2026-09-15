from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
 
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
    database_url: str | None = None  

    secret_key: str = "dev-secret-key-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours

    admin_email: str = "admin@serenitysalon.example"
    admin_password: str = "change_me_now"
    admin_seed_force_update: bool = False

    upload_dir: str = "app/uploads"
    max_upload_size_mb: int = 20
    allowed_upload_extensions: str = ".pdf,.docx,.doc"

    business_document_upload_dir: str = "app/uploads/business_documents"
    business_document_max_upload_size_mb: int = 20
    business_document_allowed_extensions: str = ".pdf,.jpg,.jpeg,.png,.webp,.docx,.doc"
    business_document_max_files_per_batch: int = 15

    
    chunk_size: int = 500  # characters
    chunk_overlap: int = 150 

    
    embedding_model_name: str = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
    embedding_dimension: int = 384
    embedding_batch_size: int = 32

    retrieval_top_k: int = 5
    retrieval_candidate_multiplier: int = 4
    keyword_boost_weight: float = 0.3
    relevance_score_threshold: float = 0.1

    max_history_exchanges: int = 16

    cancellation_window_hours: int = 24

    chat_session_retention_hours: int = 24
    slot_step_minutes: int = 30
    booking_window_days: int = 30
    max_tool_iterations: int = 4


    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    groq_temperature: float = 0.3
    groq_max_tokens: int = 300


    deepgram_api_key: str | None = None
    voice_token_ttl_seconds: int = 60
    voice_max_call_seconds: int = 900
    
    openrouter_api_key: str | None = ""
    openrouter_model: str = "openai/gpt-oss-120b"  
    openrouter_fast_model: str = ""
    openrouter_temperature: float = 0.3
    openrouter_max_tokens: int = 500
    openrouter_site_url: str = ""
    openrouter_site_name: str = ""
    
    openai_api_key: str | None = ""
    openai_model: str = "gpt-5.4-mini"
    openai_fast_model: str = ""
    openai_temperature: float = 0.3
    openai_max_tokens: int = 500
    openai_vision_model: str = "gpt-5.4-mini"

    business_name: str = " "
    business_description: str = ""

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None 
    celery_result_backend: str | None = None  
    celery_task_always_eager: bool = False

    mail_enabled: bool = False  
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    mail_from_address: str = ""
    mail_from_name: str = "Booking Desk"

    low_confidence_notification_threshold: float = 0.75
    frontend_base_url: str = "http://localhost:5173"

    business_name: str = " "
    business_description: str = ""

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
    def business_document_allowed_extensions_list(self) -> List[str]:
        return [
            ext.strip().lower()
            for ext in self.business_document_allowed_extensions.split(",")
            if ext.strip()
        ]
        
    @property
    def celery_broker_url_resolved(self) -> str:
        return self.celery_broker_url or self.redis_url


    @property
    def celery_result_backend_resolved(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()