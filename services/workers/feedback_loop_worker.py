"""
Kafka consumer worker for processing engagement feedback
Consumes outreach.events, tracks conversions, updates Thompson Sampling priors
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

# Add repository paths for local imports
REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "apps" / "agent-api"
for path in (APP_ROOT, REPO_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.config.settings import settings
from app.models.base import SessionLocal
from app.models.lead import Lead, LeadStatus
from app.models.experiment import Experiment
from app.models.outreach_log import OutreachLog, OutreachStatus

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


def update_thompson_sampling_priors(experiment: Experiment, conversion: bool):
    """
    Update Bayesian priors for Thompson Sampling

    Thompson Sampling uses Beta distribution: Beta(α, β)
    - α (alpha): Number of successes + 1
    - β (beta): Number of failures + 1

    Args:
        experiment: Experiment to update
        conversion: True if lead converted, False otherwise
    """
    if conversion:
        # Success: increment alpha (successes)
        experiment.alpha += 1.0
        logger.info(f"✅ Conversion! Updated {experiment.experiment_id}: α={experiment.alpha}, β={experiment.beta}")
    else:
        # Failure: increment beta (failures)
        experiment.beta += 1.0
        logger.debug(f"❌ No conversion. Updated {experiment.experiment_id}: α={experiment.alpha}, β={experiment.beta}")

    # Log sampling probability for debugging
    expected_value = experiment.alpha / (experiment.alpha + experiment.beta)
    logger.info(f"   Expected conversion rate: {expected_value:.2%} (will explore vs exploit)")


def process_engagement_event(event: Dict[str, Any], db: Session) -> bool:
    """
    Process engagement/conversion event and update experiment metrics

    Event types:
    - outreach.opened: Lead opened email/message
    - outreach.clicked: Lead clicked link
    - outreach.replied: Lead replied to message
    - outreach.converted: Lead became customer (SUCCESS!)

    Args:
        event: Engagement event from Kafka
        db: Database session

    Returns:
        True if successful, False otherwise
    """
    try:
        event_type = event.get("event_type", "")
        lead_id = event.get("lead_id")
        experiment_id = event.get("experiment_id")

        if not lead_id or not experiment_id:
            logger.error(f"Missing lead_id or experiment_id in event: {event}")
            return False

        # Get lead and experiment
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()

        if not lead or not experiment:
            logger.error(f"Lead {lead_id} or Experiment {experiment_id} not found")
            return False

        # Update based on event type
        if event_type == "outreach.opened":
            logger.info(f"📧 Lead {lead.lightfield_id} opened message (experiment={experiment_id})")

            # Update outreach log
            outreach_log = (
                db.query(OutreachLog)
                .filter(
                    OutreachLog.lead_id == lead_id,
                    OutreachLog.experiment_id == experiment_id
                )
                .order_by(OutreachLog.created_at.desc())
                .first()
            )
            if outreach_log:
                outreach_log.status = OutreachStatus.OPENED
                outreach_log.opened_at = datetime.now(timezone.utc)

        elif event_type == "outreach.clicked":
            logger.info(f"🔗 Lead {lead.lightfield_id} clicked link (experiment={experiment_id})")

            # Update outreach log
            outreach_log = (
                db.query(OutreachLog)
                .filter(
                    OutreachLog.lead_id == lead_id,
                    OutreachLog.experiment_id == experiment_id
                )
                .order_by(OutreachLog.created_at.desc())
                .first()
            )
            if outreach_log:
                outreach_log.status = OutreachStatus.CLICKED
                outreach_log.clicked_at = datetime.now(timezone.utc)

        elif event_type == "outreach.replied":
            logger.info(f"💬 Lead {lead.lightfield_id} replied (experiment={experiment_id})")

            # Update lead status
            lead.status = LeadStatus.RESPONDED
            lead.response_count = (lead.response_count or 0) + 1

            # Update outreach log
            outreach_log = (
                db.query(OutreachLog)
                .filter(
                    OutreachLog.lead_id == lead_id,
                    OutreachLog.experiment_id == experiment_id
                )
                .order_by(OutreachLog.created_at.desc())
                .first()
            )
            if outreach_log:
                outreach_log.status = OutreachStatus.REPLIED
                outreach_log.replied_at = datetime.now(timezone.utc)

            # Update experiment metrics
            experiment.responses_received = (experiment.responses_received or 0) + 1

        elif event_type == "outreach.converted":
            logger.info(f"🎉 CONVERSION! Lead {lead.lightfield_id} converted (experiment={experiment_id})")

            # Update lead status
            lead.status = LeadStatus.CONVERTED

            # Update experiment metrics
            experiment.conversions = (experiment.conversions or 0) + 1

            # 🎯 UPDATE THOMPSON SAMPLING PRIORS (CONVERSION = SUCCESS)
            update_thompson_sampling_priors(experiment, conversion=True)

        else:
            logger.warning(f"Unknown event type: {event_type}")
            return True  # Not an error, just unknown type

        # Recalculate experiment metrics
        experiment.update_metrics()

        # If this was a non-conversion engagement, it's still valuable feedback
        # We could optionally update priors for "no conversion yet" here
        if event_type in ["outreach.opened", "outreach.clicked", "outreach.replied"]:
            # For now, we only update priors on final conversion
            # But we could implement intermediate rewards here
            pass

        db.commit()

        logger.info(
            f"Updated metrics for experiment {experiment_id}: "
            f"conversions={experiment.conversions}, "
            f"conversion_rate={experiment.conversion_rate:.2%}"
        )

        return True

    except Exception as e:
        logger.error(f"Error processing engagement event: {e}", exc_info=True)
        sentry_sdk.capture_exception(e)
        db.rollback()
        return False


def main():
    """Main worker loop"""
    logger.info("🚀 Starting Feedback Loop Worker")

    # Kafka consumer configuration
    consumer_config = {
        'bootstrap.servers': settings.kafka_brokers,
        'group.id': 'feedback-loop',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    }

    consumer = Consumer(consumer_config)
    consumer.subscribe(['outreach.events'])

    logger.info(f"📡 Subscribed to outreach.events (brokers: {settings.kafka_brokers})")

    processed_count = 0
    conversion_count = 0
    error_count = 0

    try:
        while not shutdown_flag:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                logger.error(f"Kafka error: {msg.error()}")
                continue

            # Process message
            try:
                event = json.loads(msg.value().decode('utf-8'))
                event_type = event.get("event_type", "")

                logger.info(f"Processing {event_type} for lead {event.get('lead_id')}")

                db = SessionLocal()
                try:
                    success = process_engagement_event(event, db)
                    if success:
                        processed_count += 1
                        if event_type == "outreach.converted":
                            conversion_count += 1
                        consumer.commit()
                    else:
                        error_count += 1
                        logger.warning(f"Failed to process event {event_type}")

                finally:
                    db.close()

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing message: {e}", exc_info=True)
                sentry_sdk.capture_exception(e)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")

    finally:
        logger.info(
            f"Shutting down... (processed={processed_count}, "
            f"conversions={conversion_count}, errors={error_count})"
        )
        consumer.close()


if __name__ == "__main__":
    main()
