#!/usr/bin/env python3
"""
Simulate lead conversions for demo/testing Phase 3 feedback loop
Publishes conversion events to Kafka to trigger Thompson Sampling updates
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Add repository paths
REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "agent-api"
sys.path.insert(0, str(APP_ROOT))

from app.models.base import SessionLocal
from app.models.lead import Lead
from app.services.kafka_producer import get_kafka_producer


def simulate_conversion(lead_id: Optional[int] = None, lightfield_id: Optional[str] = None):
    """
    Simulate a lead conversion

    Args:
        lead_id: Database ID of lead
        lightfield_id: Lightfield ID of lead (alternative to lead_id)
    """
    db = SessionLocal()

    try:
        # Get lead
        if lead_id:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
        elif lightfield_id:
            lead = db.query(Lead).filter(Lead.lightfield_id == lightfield_id).first()
        else:
            # Get most recent contacted lead
            lead = (
                db.query(Lead)
                .filter(Lead.status == 'CONTACTED')
                .order_by(Lead.contacted_at.desc())
                .first()
            )

        if not lead:
            print("❌ No suitable lead found for conversion")
            return False

        if not lead.experiment_id:
            print(f"❌ Lead {lead.lightfield_id} has no experiment assigned")
            return False

        print(f"\n🎯 Simulating conversion for lead: {lead.lightfield_id}")
        print(f"   Company: {lead.company_name}")
        print(f"   Score: {lead.score}")
        print(f"   Experiment: {lead.experiment_id}")

        # Publish conversion event to Kafka
        kafka_producer = get_kafka_producer()

        conversion_event = {
            "event_type": "outreach.converted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lead_id": lead.id,
            "lightfield_id": lead.lightfield_id,
            "experiment_id": lead.experiment_id,
            "conversion_value": 1000.0,  # Demo value
            "converted_at": datetime.now(timezone.utc).isoformat(),
        }

        kafka_producer.producer.produce(
            "outreach.events",
            key=lead.lightfield_id.encode('utf-8'),
            value=json.dumps(conversion_event).encode('utf-8'),
        )
        kafka_producer.producer.flush()

        print(f"\n✅ Conversion event published to outreach.events")
        print(f"   Event type: {conversion_event['event_type']}")
        print(f"   Lead ID: {lead.id}")
        print(f"   Experiment: {lead.experiment_id}")
        print(f"\n💡 Thompson Sampling priors will be updated by feedback_loop_worker")

        return True

    except Exception as e:
        print(f"\n❌ Error simulating conversion: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def simulate_multiple_conversions(count: int = 5):
    """Simulate multiple conversions to demonstrate learning"""
    db = SessionLocal()

    try:
        # Get recent contacted leads
        leads = (
            db.query(Lead)
            .filter(Lead.status == 'CONTACTED')
            .filter(Lead.experiment_id != None)
            .order_by(Lead.contacted_at.desc())
            .limit(count)
            .all()
        )

        print(f"\n🎲 Simulating {len(leads)} conversions...")

        kafka_producer = get_kafka_producer()

        for i, lead in enumerate(leads, 1):
            print(f"\n[{i}/{len(leads)}] Converting {lead.company_name} (experiment={lead.experiment_id})")

            conversion_event = {
                "event_type": "outreach.converted",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "lead_id": lead.id,
                "lightfield_id": lead.lightfield_id,
                "experiment_id": lead.experiment_id,
                "conversion_value": 1000.0 * (i / len(leads)),  # Varying values
            }

            kafka_producer.producer.produce(
                "outreach.events",
                key=lead.lightfield_id.encode('utf-8'),
                value=json.dumps(conversion_event).encode('utf-8'),
            )

        kafka_producer.producer.flush()

        print(f"\n✅ {len(leads)} conversion events published!")
        print(f"\n💡 Run feedback_loop_worker to process these events and update Thompson Sampling priors")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simulate lead conversions for demo")
    parser.add_argument("--lead-id", type=int, help="Specific lead ID to convert")
    parser.add_argument("--lightfield-id", type=str, help="Specific lightfield ID to convert")
    parser.add_argument("--count", type=int, default=1, help="Number of conversions to simulate")

    args = parser.parse_args()

    if args.count > 1:
        simulate_multiple_conversions(args.count)
    else:
        simulate_conversion(lead_id=args.lead_id, lightfield_id=args.lightfield_id)
