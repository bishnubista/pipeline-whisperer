"""Lead model - represents a sales lead from Lightfield CRM"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from .base import Base


class LeadStatus(str, enum.Enum):
    """Lead processing status"""
    RAW = "raw"  # Just ingested from Lightfield
    SCORED = "scored"  # stackAI scoring complete
    QUEUED = "queued"  # Ready for outreach
    CONTACTED = "contacted"  # Outreach sent
    RESPONDED = "responded"  # Lead responded
    CONVERTED = "converted"  # Deal closed
    FAILED = "failed"  # Processing failed
    SNOOZED = "snoozed"  # Manually paused


class LeadPersona(str, enum.Enum):
    """Lead persona classifications from stackAI"""
    ENTERPRISE = "enterprise"  # Large company, high value
    SMB = "smb"  # Small/medium business
    STARTUP = "startup"  # Early stage company
    INDIVIDUAL = "individual"  # Solo practitioner
    UNKNOWN = "unknown"  # Not yet classified


class Lead(Base):
    """Lead model with Lightfield data and stackAI scoring"""
    __tablename__ = "leads"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Lightfield CRM data
    lightfield_id = Column(String(255), unique=True, index=True, nullable=False)
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    contact_email = Column(String(255), index=True)
    contact_title = Column(String(255))
    industry = Column(String(255))
    company_size = Column(String(50))  # e.g., "50-200"
    website = Column(String(500))

    # Raw event data from Lightfield
    raw_payload = Column(JSON)

    # stackAI scoring results
    score = Column(Float)  # 0.0-1.0 lead quality score
    persona = Column(SQLEnum(LeadPersona), default=LeadPersona.UNKNOWN)
    scoring_metadata = Column(JSON)  # stackAI response details

    # Processing status
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.RAW, index=True)
    experiment_id = Column(String(100))  # Which experiment cohort

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    scored_at = Column(DateTime(timezone=True))
    contacted_at = Column(DateTime(timezone=True))

    # Metrics
    outreach_count = Column(Integer, default=0)
    response_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<Lead {self.id}: {self.company_name} ({self.status.value})>"
