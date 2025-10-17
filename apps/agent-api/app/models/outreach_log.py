"""Outreach log model - tracks all sent outreach messages"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from .base import Base


class OutreachStatus(str, enum.Enum):
    """Outreach message status"""
    PENDING = "pending"  # Queued for sending
    SENT = "sent"  # Successfully sent
    DELIVERED = "delivered"  # Delivered confirmation received
    OPENED = "opened"  # Recipient opened message
    CLICKED = "clicked"  # Recipient clicked link
    REPLIED = "replied"  # Recipient replied
    BOUNCED = "bounced"  # Failed to deliver
    UNSUBSCRIBED = "unsubscribed"  # Recipient opted out
    FAILED = "failed"  # System error


class OutreachLog(Base):
    """Log of all outreach messages sent to leads"""
    __tablename__ = "outreach_logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    experiment_id = Column(String(100), ForeignKey("experiments.experiment_id"), nullable=False, index=True)
    template_id = Column(String(100), ForeignKey("outreach_templates.template_id"), nullable=False, index=True)

    # Message content (as actually sent)
    subject = Column(String(500))
    body = Column(Text, nullable=False)
    channel = Column(String(50), default="email")

    # Sending details
    sent_via = Column(String(100))  # e.g., "lightfield", "sendgrid", "linkedin_api"
    external_message_id = Column(String(255), index=True)  # ID from external provider

    # Status tracking
    status = Column(SQLEnum(OutreachStatus), default=OutreachStatus.PENDING, nullable=False, index=True)
    status_details = Column(JSON)  # Additional status information

    # Engagement tracking
    opened_at = Column(DateTime(timezone=True))
    clicked_at = Column(DateTime(timezone=True))
    replied_at = Column(DateTime(timezone=True))

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<OutreachLog id={self.id} lead={self.lead_id} status={self.status}>"
