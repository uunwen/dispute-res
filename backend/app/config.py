from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/dispute_resolver"
    redis_url: str = "redis://localhost:6379/0"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_model_advocate: str = ""
    llm_model_judge: str = ""
    llm_model_tools: str = ""
    llm_mock: bool = False
    llm_timeout: float = 60.0
    llm_max_retries: int = 3
    llm_backoff_base: float = 0.5
    llm_temperature: float = 0.0
    llm_max_tokens: int | None = None
    embedding_model: str = "gemini-embedding-001"
    # EMBEDDING_DIM is the single source of truth for the embedding space. The
    # API provider is asked to return this many dimensions, the fastembed model
    # must match it, and every stored/queried vector is validated against it.
    # 384 keeps the vector type indexable by pgvector HNSW/IVFFlat (<= 2000).
    embedding_dim: int = 384
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    fastembed_model: str = "BAAI/bge-small-en-v1.5"

    route_buffer_m: float = 100.0
    route_min_extra_km: float = 2.0
    route_min_fraction_outside: float = 0.2
    route_traffic_speed_kmh: float = 15.0
    stop_duration_min: float = 2.0
    noshow_proximity_m: float = 100.0
    noshow_min_wait_min: float = 5.0
    abuse_risk_threshold: float = 0.6
    escalation_enabled: bool = True
    escalation_threshold: float = 0.65
    fraud_dispute_frequency_days: int = 30
    fraud_dispute_frequency_threshold: int = 3
    fraud_win_rate_threshold: float = 0.4
    fraud_repeat_deviation_threshold: int = 2
    fraud_account_age_days: int = 14
    fraud_penalty_threshold: float = 0.5
    fraud_penalty_weight: float = 0.2
    sla_safety_seconds: int = 3600
    sla_default_seconds: int = 86400

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
