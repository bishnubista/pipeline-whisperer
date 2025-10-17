#!/usr/bin/env python3
"""
Demo script: Generate leads and publish to Kafka
Simulates Lightfield CRM webhook sending leads to Pipeline Whisperer
"""
import sys
import logging
import time
from pathlib import Path

# Add repository paths for imports so the script works on any machine
REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "agent-api"
for path in (APP_ROOT, REPO_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from services.simulators.lightfield_simulator import LightfieldSimulator
from app.services.kafka_producer import get_kafka_producer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Generate and publish demo leads"""
    print("=" * 80)
    print("PIPELINE WHISPERER - LEAD INGESTION DEMO")
    print("=" * 80)
    print()

    # Initialize
    simulator = LightfieldSimulator(seed=42)
    producer = get_kafka_producer()

    # Configuration
    num_leads = int(input("How many leads to generate? [default: 10]: ") or "10")
    delay = float(input("Delay between leads (seconds)? [default: 1.0]: ") or "1.0")

    print()
    print(f"📊 Generating {num_leads} leads with {delay}s delay...")
    print()

    # Generate and publish
    published_count = 0
    failed_count = 0

    for i, lead in enumerate(simulator.stream_leads(count=num_leads, delay_seconds=delay), 1):
        company = lead['company']['name']
        contact = lead['contact']['name']

        print(f"[{i}/{num_leads}] Publishing: {company} - {contact}")

        success = producer.publish_lead(lead)
        if success:
            published_count += 1
            print(f"  ✅ Published to Kafka")
        else:
            failed_count += 1
            print(f"  ❌ Failed to publish")

    # Flush remaining messages
    print()
    print("Flushing Kafka producer...")
    producer.flush(timeout=10.0)

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Published: {published_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📈 Total: {num_leads}")
    print()
    print("Next steps:")
    print("  1. Start worker: uv run python services/workers/lead_scorer_worker.py")
    print("  2. Check database: sqlite3 apps/agent-api/pipeline.db 'SELECT * FROM leads;'")
    print("=" * 80)


if __name__ == "__main__":
    main()
