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

    # Database
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

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
