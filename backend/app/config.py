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
    # Cap the number of LLM tool-calling rounds an advocate may perform after the
    # deterministic evidence has been precomputed and handed to them.
    advocate_max_tool_calls: int = 2
    # Whether the advocates run a second rebuttal round at all.
    rebuttal_enabled: bool = True
    embedding_model: str = "gemini-embedding-001"
    # EMBEDDING_DIM is the single source of truth for the embedding space. The
    # API provider is asked to return this many dimensions, the fastembed model
    # must match it, and every stored/queried vector is validated against it.
    # 384 keeps the vector type indexable by pgvector HNSW/IVFFlat (<= 2000).
    embedding_dim: int = 384
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    fastembed_model: str = "BAAI/bge-small-en-v1.5"
    # Minimum cosine similarity (1 - cosine_distance) a policy chunk must reach to
    # be returned; lower-similarity chunks are dropped from retrieval results.
    embedding_similarity_cutoff: float = 0.25

    route_buffer_m: float = 100.0
    # Policy v2.1 Section 1.3: deviation tolerance is 1 km.
    route_min_extra_km: float = 1.0
    route_min_fraction_outside: float = 0.2
    route_traffic_speed_kmh: float = 15.0
    # Policy v2.1 Section 6.2: escalate when deviation exceeds 2 km.
    route_escalate_km: float = 2.0
    stop_duration_min: float = 2.0
    noshow_proximity_m: float = 100.0
    # Policy v2.1 Section 2.1: free wait time is 5 minutes from scheduled pickup.
    noshow_min_wait_min: float = 5.0
    # Policy v2.1 Section 2.2: no-show cancellation fee is $5.00.
    noshow_cancellation_fee: float = 5.0
    # Policy v2.1 Section 2.4: rider goodwill credit when the driver no-shows
    # without any contact attempt.
    noshow_goodwill_credit: float = 5.0
    abuse_risk_threshold: float = 0.6
    escalation_enabled: bool = True
    # Policy v2.1 Section 6.1 monetary thresholds (disputed amount = actual fare):
    # below escalation_low_value -> final at any confidence; between low and high
    # -> confidence threshold applies; above high -> always escalate.
    escalation_low_value: float = 10.0
    escalation_high_value: float = 50.0
    # Policy v2.1 Section 6.1: confidence threshold for the $10-50 band.
    escalation_threshold: float = 0.80
    # Policy v2.1 Section 6.3: raised threshold when a party has a fraud flag.
    escalation_fraud_threshold: float = 0.95
    # Policy v2.1 Section 5.2: safety terms that force escalation regardless of
    # the selected dispute category.
    safety_keywords: list[str] = [
        "threat", "threaten", "harass", "assault", "abuse", "dangerous",
        "reckless", "unsafe", "sexual", "inappropriate", "emergency", "sos",
        "weapon", "violence", "scared", "fear", "hurt", "attack",
    ]
    fraud_dispute_frequency_days: int = 30
    fraud_dispute_frequency_threshold: int = 3
    fraud_win_rate_threshold: float = 0.4
    fraud_repeat_deviation_threshold: int = 2
    fraud_account_age_days: int = 14
    fraud_penalty_threshold: float = 0.5
    fraud_penalty_weight: float = 0.2
    sla_safety_seconds: int = 3600
    sla_default_seconds: int = 86400
    # Max concurrent dispute resolutions when running the evaluation harness.
    eval_concurrency: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
