"""
Kafka consumer worker for orchestrating outreach
Consumes from leads.scored, generates personalized messages, sends via Lightfield, publishes events
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
from app.models.outreach_template import OutreachTemplate
from app.models.outreach_log import OutreachLog, OutreachStatus
from app.services import (
    get_kafka_producer,
    get_truefoundry_client,
    get_lightfield_client,
)

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


def select_experiment(db: Session, lead: Lead) -> Optional[Experiment]:
    """
    Select experiment using Thompson Sampling (multi-armed bandit)

    Args:
        db: Database session
        lead: The lead to assign to an experiment

    Returns:
        Selected experiment or None if no active experiments
    """
    import random

    # Get all active experiments for this persona
    experiments = (
        db.query(Experiment)
        .filter(Experiment.is_active == True)
        .all()
    )

    if not experiments:
        logger.warning("No active experiments found")
        return None

    # Thompson Sampling: sample from Beta distribution for each experiment
    best_experiment = None
    best_sample = -1

    for exp in experiments:
        # Sample from Beta(alpha, beta)
        sample = random.betavariate(exp.alpha, exp.beta)
        logger.debug(f"Experiment {exp.experiment_id}: sampled {sample:.4f} (α={exp.alpha}, β={exp.beta})")

        if sample > best_sample:
            best_sample = sample
            best_experiment = exp

    logger.info(f"Selected experiment: {best_experiment.experiment_id} (sample={best_sample:.4f})")
    return best_experiment


def get_template_for_experiment(db: Session, experiment: Experiment) -> Optional[OutreachTemplate]:
    """Get an active template for the given experiment"""
    template = (
        db.query(OutreachTemplate)
        .filter(
            OutreachTemplate.experiment_id == experiment.experiment_id,
            OutreachTemplate.is_active == True,
        )
        .first()
    )

    if not template:
        logger.warning(f"No active template found for experiment {experiment.experiment_id}")

    return template


def process_scored_lead(event: Dict[str, Any], db: Session) -> bool:
    """
    Process a scored lead event and orchestrate outreach

    Flow:
    1. Select experiment (Thompson Sampling)
    2. Get template for experiment
    3. Generate personalized message (Truefoundry)
    4. Send via Lightfield
    5. Log outreach
    6. Publish event to outreach.events

    Args:
        event: Scored lead event from Kafka
        db: Database session

    Returns:
        True if successful, False otherwise
    """
    try:
        lightfield_id = event.get("lightfield_id")
        if not lightfield_id:
            logger.error("Missing lightfield_id in event")
            return False

        # Get lead from database
        lead = db.query(Lead).filter(Lead.lightfield_id == lightfield_id).first()
        if not lead:
            logger.error(f"Lead not found: {lightfield_id}")
            return False

        # Skip if already contacted
        if lead.status in [LeadStatus.CONTACTED, LeadStatus.RESPONDED, LeadStatus.CONVERTED]:
            logger.info(f"Lead {lightfield_id} already contacted (status={lead.status})")
            return True

        # Skip if score is too low (< 0.5)
        if lead.score is None or lead.score < 0.5:
            logger.info(f"Lead {lightfield_id} score too low ({lead.score}), skipping outreach")
            return True

        # Select experiment
        experiment = select_experiment(db, lead)
        if not experiment:
            logger.error("No experiment available")
            return False

        # Get template
        template = get_template_for_experiment(db, experiment)
        if not template:
            logger.error(f"No template for experiment {experiment.experiment_id}")
            return False

        # Prepare lead data for personalization
        lead_data = {
            "contact_name": lead.contact_name or "there",
            "company_name": lead.company_name,
            "industry": lead.industry or "your industry",
            "persona": lead.persona or "professional",
            "score": lead.score,
        }

        # Generate personalized message via Truefoundry
        truefoundry = get_truefoundry_client()
        message = truefoundry.generate_personalized_message(
            template=template.body_template,
            lead_data=lead_data,
            personalization_prompt=template.personalization_prompt,
            config=template.config or {},
        )

        # Send via Lightfield
        lightfield = get_lightfield_client()
        send_result = lightfield.send_email(
            to_email=lead.contact_email,
            to_name=lead.contact_name or lead.company_name,
            subject=message.get("subject", template.subject_line or "Quick intro"),
            body=message.get("body", ""),
            tracking_id=f"lead_{lead.id}_exp_{experiment.experiment_id}",
        )

        if send_result.get("status") != "sent":
            logger.error(f"Failed to send message: {send_result.get('error')}")
            return False

        # Create outreach log
        outreach_log = OutreachLog(
            lead_id=lead.id,
            experiment_id=experiment.experiment_id,
            template_id=template.template_id,
            subject=message.get("subject", ""),
            body=message.get("body", ""),
            channel=template.channel,
            sent_via=send_result.get("provider", "lightfield"),
            external_message_id=send_result.get("message_id"),
            status=OutreachStatus.SENT,
            sent_at=send_result.get("sent_at") or datetime.now(timezone.utc),
        )
        db.add(outreach_log)

        # Update lead
        lead.status = LeadStatus.CONTACTED
        lead.experiment_id = experiment.experiment_id
        lead.contacted_at = datetime.now(timezone.utc)
        lead.outreach_count = (lead.outreach_count or 0) + 1

        # Update experiment metrics
        experiment.leads_assigned = (experiment.leads_assigned or 0) + 1
        experiment.outreach_sent = (experiment.outreach_sent or 0) + 1
        experiment.update_metrics()

        db.commit()

        # Publish outreach event to Kafka
        kafka_producer = get_kafka_producer()
        outreach_event = {
            "event_type": "outreach.sent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lead_id": lead.id,
            "lightfield_id": lead.lightfield_id,
            "experiment_id": experiment.experiment_id,
            "template_id": template.template_id,
            "channel": template.channel,
            "message_id": send_result.get("message_id"),
            "subject": message.get("subject", ""),
        }
        kafka_producer.producer.produce(
            "outreach.events",
            key=lightfield_id.encode('utf-8'),
            value=json.dumps(outreach_event).encode('utf-8'),
        )
        kafka_producer.producer.flush()

        logger.info(
            f"✅ Outreach sent: lead={lightfield_id}, "
            f"experiment={experiment.experiment_id}, "
            f"message_id={send_result.get('message_id')}"
        )

        return True

    except Exception as e:
        logger.error(f"Error processing scored lead: {e}", exc_info=True)
        sentry_sdk.capture_exception(e)
        db.rollback()
        return False


def main():
    """Main worker loop"""
    logger.info("🚀 Starting Outreach Orchestrator Worker")

    # Kafka consumer configuration
    consumer_config = {
        'bootstrap.servers': settings.kafka_brokers,
        'group.id': 'outreach-orchestrator',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    }

    consumer = Consumer(consumer_config)
    consumer.subscribe(['leads.scored'])

    logger.info(f"📡 Subscribed to leads.scored (brokers: {settings.kafka_brokers})")

    processed_count = 0
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
                logger.info(f"Processing scored lead: {event.get('lightfield_id')}")

                db = SessionLocal()
                try:
                    success = process_scored_lead(event, db)
                    if success:
                        processed_count += 1
                        consumer.commit()
                    else:
                        error_count += 1
                        logger.warning(f"Failed to process lead {event.get('lightfield_id')}")

                finally:
                    db.close()

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing message: {e}", exc_info=True)
                sentry_sdk.capture_exception(e)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")

    finally:
        logger.info(f"Shutting down... (processed={processed_count}, errors={error_count})")
        consumer.close()


if __name__ == "__main__":
    main()
