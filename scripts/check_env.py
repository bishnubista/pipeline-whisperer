#!/usr/bin/env python3
"""
Environment check script - verifies all Phase 1 requirements
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "agent-api"
sys.path.insert(0, str(APP_ROOT))

from app.config.settings import settings

def check_env():
    """Check environment configuration"""
    print("=" * 80)
    print("PIPELINE WHISPERER - ENVIRONMENT CHECK")
    print("=" * 80)
    print()

    issues = []
    warnings = []

    # Required for Phase 1
    print("📋 Phase 1 Requirements:")
    print()

    # Database
    print(f"✅ Database: {settings.database_url}")
    if "sqlite" in settings.database_url:
        db_path = settings.database_url.replace("sqlite:///", "")
        if Path(db_path).exists():
            print(f"   Database file exists: {db_path}")
        else:
            warnings.append(f"Database file not found (will be created): {db_path}")

    # Kafka/Redpanda
    print(f"✅ Kafka Brokers: {settings.redpanda_brokers}")
    print(f"✅ Topics:")
    print(f"   - {settings.kafka_topic_leads_raw}")
    print(f"   - {settings.kafka_topic_leads_scored}")
    print(f"   - {settings.kafka_topic_outreach_events}")

    # API Settings
    print(f"✅ API: {settings.api_host}:{settings.api_port}")
    print(f"✅ Demo Mode: {settings.demo_mode}")
    print(f"✅ Log Level: {settings.log_level}")
    print()

    # Optional API Keys
    print("🔑 API Keys (Optional for Phase 1):")
    print()

    # OpenAI scoring
    if settings.openai_api_key and "your_" not in settings.openai_api_key:
        print(f"✅ OpenAI API Key: {settings.openai_api_key[:6]}***")
        print(f"✅ OpenAI model: {settings.openai_model}")
    else:
        warnings.append("OpenAI API key not configured (using mock scoring)")

    # Sentry
    if settings.sentry_dsn_python and "your_" not in settings.sentry_dsn_python:
        print(f"✅ Sentry (Python): Configured")
    else:
        warnings.append("Sentry DSN not configured (monitoring disabled)")

    # Lightfield (not needed for Phase 1)
    if settings.lightfield_api_key and settings.lightfield_api_key != "your_lightfield_api_key_here":
        print(f"✅ Lightfield API Key: Configured")
    else:
        print(f"ℹ️  Lightfield API Key: Not configured (using simulator)")

    # Truefoundry (not needed for Phase 1)
    if settings.truefoundry_api_key and settings.truefoundry_api_key != "your_truefoundry_api_key_here":
        print(f"✅ Truefoundry API Key: Configured")
    else:
        print(f"ℹ️  Truefoundry API Key: Not configured (Phase 2)")

    print()
    print("=" * 80)

    # Summary
    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
        print()
        return False
    elif warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
        print("✅ Environment is ready for Phase 1 testing (with warnings)")
        print()
        return True
    else:
        print("✅ Environment is fully configured!")
        print()
        return True

if __name__ == "__main__":
    success = check_env()
    sys.exit(0 if success else 1)
