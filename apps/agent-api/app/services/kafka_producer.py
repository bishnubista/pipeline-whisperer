"""Kafka producer service for publishing events to Redpanda"""
import json
import logging
from typing import Dict, Any
from confluent_kafka import Producer
from confluent_kafka.error import KafkaException
import sentry_sdk

from app.config.settings import settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    """Kafka producer for publishing lead events to Redpanda"""

    def __init__(self):
        """Initialize Kafka producer"""
        self.config = {
            'bootstrap.servers': settings.redpanda_brokers,
            'client.id': 'pipeline-whisperer-producer',
            'acks': 'all',  # Wait for all replicas
            'retries': 3,
            'max.in.flight.requests.per.connection': 5,
        }
        self.producer = Producer(self.config)
        logger.info(f"Kafka producer initialized: {settings.redpanda_brokers}")

    def delivery_report(self, err, msg):
        """Callback for message delivery reports"""
        if err is not None:
            error_msg = f"Message delivery failed: {err}"
            logger.error(error_msg)
            sentry_sdk.capture_message(error_msg, level="error")
        else:
            logger.debug(
                f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}"
            )

    def publish_lead(self, lead_data: Dict[str, Any]) -> bool:
        """
        Publish a lead event to the leads.raw topic

        Args:
            lead_data: Lead event payload from Lightfield

        Returns:
            bool: True if successfully queued, False otherwise
        """
        try:
            # Serialize to JSON
            message = json.dumps(lead_data).encode('utf-8')

            # Use lightfield_id as key for partitioning
            key = lead_data.get('lightfield_id', '').encode('utf-8')

            # Produce message
            self.producer.produce(
                topic=settings.kafka_topic_leads_raw,
                key=key,
                value=message,
                callback=self.delivery_report
            )

            # Trigger delivery reports
            self.producer.poll(0)

            logger.info(f"Published lead to Kafka: {lead_data.get('lightfield_id')}")
            return True

        except KafkaException as e:
            error_msg = f"Kafka error publishing lead: {e}"
            logger.error(error_msg)
            sentry_sdk.capture_exception(e)
            return False
        except Exception as e:
            error_msg = f"Unexpected error publishing lead: {e}"
            logger.error(error_msg)
            sentry_sdk.capture_exception(e)
            return False

    def publish_scored_lead(self, lead_data: Dict[str, Any]) -> bool:
        """
        Publish a scored lead to the leads.scored topic

        Args:
            lead_data: Scored lead with stackAI results

        Returns:
            bool: True if successfully queued, False otherwise
        """
        try:
            message = json.dumps(lead_data).encode('utf-8')
            key = lead_data.get('lightfield_id', '').encode('utf-8')

            self.producer.produce(
                topic=settings.kafka_topic_leads_scored,
                key=key,
                value=message,
                callback=self.delivery_report
            )

            self.producer.poll(0)
            logger.info(f"Published scored lead to Kafka: {lead_data.get('lightfield_id')}")
            return True

        except Exception as e:
            logger.error(f"Error publishing scored lead: {e}")
            sentry_sdk.capture_exception(e)
            return False

    def flush(self, timeout: float = 10.0):
        """
        Wait for all messages to be delivered

        Args:
            timeout: Maximum time to wait in seconds
        """
        remaining = self.producer.flush(timeout)
        if remaining > 0:
            logger.warning(f"{remaining} messages were not delivered within timeout")
        else:
            logger.info("All messages delivered successfully")

    def close(self):
        """Close the producer and flush pending messages"""
        logger.info("Closing Kafka producer...")
        self.flush()
        # Producer doesn't have explicit close, flush is sufficient


# Singleton instance
_producer_instance = None


def get_kafka_producer() -> KafkaProducerService:
    """Get or create Kafka producer singleton"""
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = KafkaProducerService()
    return _producer_instance
