"""Application settings and configuration"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repository paths for defaults (avoids cwd-dependent behavior)
APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = APP_ROOT / "pipeline.db"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Security
    api_key_required: bool = False
    api_keys: str = ""  # Comma-separated list of valid API keys
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    enable_https: bool = False

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Database
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600

    # Redis Cache
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    cache_ttl_seconds: int = 300  # 5 minutes

    # Redpanda/Kafka
    redpanda_brokers: str = "localhost:19092"
    kafka_topic_leads_raw: str = "leads.raw"
    kafka_topic_leads_scored: str = "leads.scored"
    kafka_topic_outreach_events: str = "outreach.events"
    kafka_timeout_seconds: int = 30

    # Sentry
    sentry_dsn_python: str | None = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 1.0
    sentry_profiles_sample_rate: float = 1.0

    # Lightfield CRM
    lightfield_api_key: str | None = None
    lightfield_base_url: str = "https://api.lightfield.ai/v1"
    lightfield_timeout_seconds: float = 30.0
    lightfield_retry_attempts: int = 3

    # OpenAI scoring
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: float = 30.0
    openai_retry_attempts: int = 3
    openai_max_tokens: int = 500

    # Truefoundry
    truefoundry_api_key: str | None = None
    truefoundry_workspace: str | None = None
    truefoundry_base_url: str = "https://api.truefoundry.com"
    truefoundry_timeout_seconds: float = 30.0
    truefoundry_retry_attempts: int = 3

    # Demo mode
    demo_mode: bool = True
    simulate_lightfield: bool = True
    log_level: str = "INFO"

    # Performance
    enable_compression: bool = True
    worker_count: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra env vars for Next.js, etc.
    )


settings = Settings()
