"""
Kafka consumer worker for processing raw leads
Consumes from leads.raw, scores with OpenAI, persists to DB, publishes to leads.scored
"""
import json
import logging
import sys
import signal
from pathlib import Path
from typing import Dict, Any, Optional
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
from app.services.openai_scoring_client import get_openai_scoring_client, OpenAIScoringClient

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
        self.scoring_client: OpenAIScoringClient = get_openai_scoring_client()

        logger.info(f"Lead scorer worker initialized")
        logger.info(f"Subscribed to: {settings.kafka_topic_leads_raw}")

        # Check scoring client status
        health = self.scoring_client.health_check()
        logger.info(f"Scoring client status: {health.get('status')}")

    def score_lead_with_openai(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score lead using OpenAI API

        Args:
            lead_data: Raw lead data from Lightfield

        Returns:
            Scoring results with score and persona
        """
        # Extract company data for scoring
        company = lead_data.get('company', {})
        metadata = lead_data.get('metadata', {})

        scoring_input = self._prepare_scoring_payload(company, metadata)

        # Call scoring client
        result = self.scoring_client.score_lead(scoring_input)

        persona_enum = self._to_persona_enum(result.get('persona'))

        return {
            'score': float(result.get('score', 0.5)),
            'persona': persona_enum.value,
            'confidence': result.get('confidence'),
            'reasoning': result.get('reasoning', 'OpenAI scoring'),
            'model_version': result.get('model_version', 'openai-v1.0'),
            'mock': result.get('mock', False),
            'scoring_input': scoring_input,
            'raw_response': result,
            'scored_at': datetime.now(timezone.utc).isoformat(),
        }

    def _to_persona_enum(self, persona_value: Optional[str]) -> LeadPersona:
        """Safely convert persona string to LeadPersona enum"""
        if not persona_value:
            return LeadPersona.UNKNOWN
        persona_value = persona_value.lower()
        try:
            return LeadPersona(persona_value)
        except ValueError:
            return LeadPersona.UNKNOWN

    def _prepare_scoring_payload(self, company: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Lightfield company payload for scoring model input"""
        size_bucket = company.get('size') or metadata.get('company_size')
        budget_range = metadata.get('budget_range') or metadata.get('spend')

        return {
            "company_name": company.get('name') or "Unknown",
            "industry": company.get('industry') or metadata.get('industry') or "unknown",
            "employee_count": self._estimate_employee_count(size_bucket),
            "revenue": self._estimate_revenue(budget_range),
            "website": company.get('website') or metadata.get('website') or "",
        }

    def _estimate_employee_count(self, size: Optional[str]) -> int:
        """Translate company size labels into approximate employee counts"""
        if not size:
            return 0

        size = size.strip().lower()
        bucket_map = {
            "1-10": (1, 10),
            "11-50": (11, 50),
            "51-200": (51, 200),
            "201-1000": (201, 1000),
        }

        if size.endswith("+"):
            try:
                lower = int(size.rstrip("+"))
                upper = lower * 2
                return (lower + upper) // 2
            except ValueError:
                return 0

        if size in bucket_map:
            lower, upper = bucket_map[size]
            return (lower + upper) // 2

        if "-" in size:
            lower_str, upper_str = size.split("-", maxsplit=1)
            try:
                lower = int(lower_str)
                upper = int(upper_str)
                return (lower + upper) // 2
            except ValueError:
                return 0

        try:
            return int(size)
        except ValueError:
            return 0

    def _estimate_revenue(self, budget_range: Optional[str]) -> float:
        """Estimate company revenue from budget/tier information"""
        if not budget_range:
            return 0.0

        budget_range = budget_range.strip().lower()
        bucket_estimates = {
            "<10k": 50_000,
            "10k-50k": 200_000,
            "50k-100k": 500_000,
            "100k-500k": 2_500_000,
            "500k+": 6_000_000,
        }

        if budget_range in bucket_estimates:
            return float(bucket_estimates[budget_range])

        if "-" in budget_range:
            lower_str, upper_str = budget_range.split("-", maxsplit=1)
            try:
                lower = float(lower_str.replace("k", "000").replace("$", ""))
                upper = float(upper_str.replace("k", "000").replace("$", ""))
                return (lower + upper) / 2.0
            except ValueError:
                return 0.0

        if budget_range.endswith("+"):
            try:
                value = float(budget_range.rstrip("+").replace("k", "000").replace("$", ""))
                return value * 1.5
            except ValueError:
                return 0.0

        return 0.0

    def _build_scoring_metadata(self, scoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare metadata payload for persistence"""
        return {
            "reasoning": scoring_result.get("reasoning"),
            "model_version": scoring_result.get("model_version"),
            "confidence": scoring_result.get("confidence"),
            "mock": scoring_result.get("mock", False),
            "scoring_input": scoring_result.get("scoring_input"),
            "raw_response": scoring_result.get("raw_response"),
            "scored_at": scoring_result.get("scored_at"),
        }

    def _build_public_scoring_payload(self, scoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trim scoring payload for downstream events"""
        return {
            "score": scoring_result.get("score"),
            "persona": scoring_result.get("persona"),
            "reasoning": scoring_result.get("reasoning"),
            "model_version": scoring_result.get("model_version"),
            "mock": scoring_result.get("mock", False),
            "confidence": scoring_result.get("confidence"),
            "scoring_input": scoring_result.get("scoring_input"),
            "scored_at": scoring_result.get("scored_at"),
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

            # Score with OpenAI
            scoring_result = self.score_lead_with_openai(lead_data)
            score_value = float(scoring_result.get('score', 0.0))
            persona_enum = self._to_persona_enum(scoring_result.get('persona'))
            logger.info(f"Scored lead {lightfield_id}: {score_value:.3f} ({persona_enum.value})")

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
                score=score_value,
                persona=persona_enum,
                scoring_metadata=self._build_scoring_metadata(scoring_result),
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
                'scoring': self._build_public_scoring_payload(scoring_result),
                'db_id': lead.id,
                'processed_at': datetime.now(timezone.utc).isoformat(),
            }
            self.producer.publish_scored_lead(scored_event)

            # Send success metric to Sentry
            sentry_sdk.capture_message(
                f"Lead scored successfully: {lightfield_id}",
                level="info",
                extras={
                    "score": score_value,
                    "persona": persona_enum.value,
                    "mock_scoring": scoring_result.get('mock', False),
                }
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
