"""
Kafka consumer worker for processing raw leads
Consumes from leads.raw, scores with stackAI, persists to DB, publishes to leads.scored
"""
import json
import logging
import sys
import signal
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone
from confluent_kafka import Consumer, KafkaException
from sqlalchemy.orm import Session
import sentry_sdk

# Add repository paths for local imports (avoids machine-specific absolute paths)
REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "apps" / "agent-api"
for path in (APP_ROOT, REPO_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.config.settings import settings
from app.models.base import SessionLocal
from app.models.lead import Lead, LeadStatus, LeadPersona
from app.services.kafka_producer import get_kafka_producer
from app.services.stackai_client import get_stackai_client

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Graceful shutdown flag
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class LeadScorerWorker:
    """Worker that consumes raw leads, scores them, and persists to database"""

    def __init__(self):
        """Initialize consumer and dependencies"""
        self.consumer_config = {
            'bootstrap.servers': settings.redpanda_brokers,
            'group.id': 'lead-scorer-group',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,  # Manual commit for reliability
            'max.poll.interval.ms': 300000,  # 5 minutes
        }
        self.consumer = Consumer(self.consumer_config)
        self.consumer.subscribe([settings.kafka_topic_leads_raw])

        self.producer = get_kafka_producer()
        self.db: Session = SessionLocal()
        self.stackai_client = get_stackai_client()

        logger.info(f"Lead scorer worker initialized")
        logger.info(f"Subscribed to: {settings.kafka_topic_leads_raw}")

        # Check Stack AI client status
        health = self.stackai_client.health_check()
        logger.info(f"Stack AI status: {health['status']}")

    def score_lead_with_stackai(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score lead using Stack AI API

        Args:
            lead_data: Raw lead data from Lightfield

        Returns:
            Scoring results with score and persona
        """
        # Extract company data for Stack AI
        company = lead_data.get('company', {})
        metadata = lead_data.get('metadata', {})

        # Map Lightfield data to Stack AI format
        stackai_input = {
            "company_name": company.get('name', 'Unknown'),
            "industry": company.get('industry', 'unknown'),
            "employee_count": self._parse_employee_count(company.get('size', '1-10')),
            "revenue": self._estimate_revenue(metadata.get('budget_range', 'unknown')),
            "website": company.get('website', ''),
        }

        # Call Stack AI client
        result = self.stackai_client.score_lead(stackai_input)

        # Map personas to our enum
        persona_map = {
            "enterprise": LeadPersona.ENTERPRISE,
            "smb": LeadPersona.SMB,
            "startup": LeadPersona.STARTUP,
            "individual": LeadPersona.INDIVIDUAL,
        }

        persona_value = result.get('persona', 'smb').lower()
        persona = persona_map.get(persona_value, LeadPersona.SMB)

        return {
            'score': result.get('score', 0.5),
            'persona': persona.value,
            'confidence': 0.85,  # Stack AI doesn't return confidence, use default
            'reasoning': result.get('reasoning', 'Stack AI scoring'),
            'model_version': 'stackai-v1.0',
            'is_mock': result.get('mock', False),
        }

    def _parse_employee_count(self, size_range: str) -> int:
        """Convert employee size range to approximate number"""
        size_map = {
            '1-10': 5,
            '11-50': 30,
            '51-200': 125,
            '201-1000': 600,
            '1000+': 2000,
        }
        return size_map.get(size_range, 50)

    def _estimate_revenue(self, budget_range: str) -> int:
        """Estimate company revenue from budget range"""
        # Rough heuristic: budget is usually 10-20% of revenue
        budget_map = {
            'unknown': 1_000_000,
            '<10k': 100_000,
            '10k-50k': 500_000,
            '50k-100k': 1_000_000,
            '100k-500k': 5_000_000,
            '500k+': 15_000_000,
        }
        return budget_map.get(budget_range, 1_000_000)

    def _mock_stackai_scoring(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock stackAI scoring for demo purposes"""
        import random

        company = lead_data.get('company', {})
        metadata = lead_data.get('metadata', {})

        # Simple scoring logic based on company size and budget
        score = 0.5
        if company.get('size') in ['201-1000', '1000+']:
            score += 0.2
        if metadata.get('budget_range') in ['100k-500k', '500k+']:
            score += 0.2
        if metadata.get('timeline') in ['immediate', '1-3 months']:
            score += 0.1

        # Add some randomness
        score = min(1.0, score + random.uniform(-0.1, 0.1))

        # Determine persona
        size = company.get('size', '1-10')
        if size == '1000+':
            persona = LeadPersona.ENTERPRISE
        elif size in ['201-1000', '51-200']:
            persona = LeadPersona.SMB
        elif size == '11-50':
            persona = LeadPersona.STARTUP
        else:
            persona = LeadPersona.INDIVIDUAL

        return {
            'score': round(score, 3),
            'persona': persona.value,
            'confidence': 0.85,
            'reasoning': f"Company size {size}, budget {metadata.get('budget_range')}",
            'model_version': 'mock-v1.0',
        }

    def process_lead(self, lead_data: Dict[str, Any]):
        """Process a single lead: score, persist, publish"""
        lightfield_id = lead_data.get('lightfield_id')
        logger.info(f"Processing lead: {lightfield_id}")

        try:
            # Check if lead already exists
            existing_lead = self.db.query(Lead).filter(
                Lead.lightfield_id == lightfield_id
            ).first()

            if existing_lead:
                logger.info(f"Lead {lightfield_id} already processed, skipping")
                return

            # Score with stackAI
            scoring_result = self.score_lead_with_stackai(lead_data)
            logger.info(f"Scored lead {lightfield_id}: {scoring_result['score']:.3f}")

            # Create Lead record
            company = lead_data.get('company', {})
            contact = lead_data.get('contact', {})

            lead = Lead(
                lightfield_id=lightfield_id,
                company_name=company.get('name'),
                contact_name=contact.get('name'),
                contact_email=contact.get('email'),
                contact_title=contact.get('title'),
                industry=company.get('industry'),
                company_size=company.get('size'),
                website=company.get('website'),
                raw_payload=lead_data,
                score=scoring_result['score'],
                persona=LeadPersona(scoring_result['persona']),
                scoring_metadata=scoring_result,
                status=LeadStatus.SCORED,
                scored_at=datetime.now(timezone.utc),
            )

            # Persist to database
            self.db.add(lead)
            self.db.commit()
            self.db.refresh(lead)

            logger.info(f"Persisted lead {lightfield_id} to database (ID: {lead.id})")

            # Publish scored lead to leads.scored topic
            scored_event = {
                **lead_data,
                'scoring': scoring_result,
                'db_id': lead.id,
                'processed_at': datetime.now(timezone.utc).isoformat(),
            }
            self.producer.publish_scored_lead(scored_event)

            # Send success metric to Sentry
            sentry_sdk.capture_message(
                f"Lead scored successfully: {lightfield_id}",
                level="info",
                extras={"score": scoring_result['score'], "persona": scoring_result['persona']}
            )

        except Exception as e:
            logger.error(f"Error processing lead {lightfield_id}: {e}")
            sentry_sdk.capture_exception(e)
            self.db.rollback()
            raise

    def run(self):
        """Main consumer loop"""
        logger.info("Starting lead scorer worker...")

        try:
            while not shutdown_flag:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    raise KafkaException(msg.error())

                # Parse message
                try:
                    lead_data = json.loads(msg.value().decode('utf-8'))
                    self.process_lead(lead_data)

                    # Commit offset after successful processing
                    self.consumer.commit(msg)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Don't commit - message will be reprocessed

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            logger.info("Shutting down worker...")
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Closing consumer and database connection...")
        self.consumer.close()
        self.db.close()
        self.producer.close()
        logger.info("Worker shutdown complete")


def main():
    """Entry point"""
    logger.info("=" * 80)
    logger.info("LEAD SCORER WORKER")
    logger.info("=" * 80)

    worker = LeadScorerWorker()
    worker.run()


if __name__ == "__main__":
    main()
