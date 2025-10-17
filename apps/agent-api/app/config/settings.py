"""Application settings and configuration"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Database
    database_url: str = "sqlite:///./pipeline.db"

    # Redpanda/Kafka
    redpanda_brokers: str = "localhost:19092"
    kafka_topic_leads_raw: str = "leads.raw"
    kafka_topic_leads_scored: str = "leads.scored"
    kafka_topic_outreach_events: str = "outreach.events"

    # Sentry
    sentry_dsn_python: str | None = None
    sentry_environment: str = "development"

    # Lightfield CRM
    lightfield_api_key: str | None = None
    lightfield_base_url: str = "https://api.lightfield.ai/v1"

    # stackAI
    stackai_api_key: str | None = None
    stackai_project_id: str | None = None

    # Truefoundry
    truefoundry_api_key: str | None = None
    truefoundry_workspace: str | None = None
    truefoundry_base_url: str = "https://api.truefoundry.com"

    # Demo mode
    demo_mode: bool = True
    simulate_lightfield: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
