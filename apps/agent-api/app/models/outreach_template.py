"""Outreach template model - stores message templates for experiments"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from .base import Base


class OutreachTemplate(Base):
    """Template for outreach messages (email/LinkedIn/etc.)"""
    __tablename__ = "outreach_templates"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Template metadata
    template_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))

    # Associated experiment
    experiment_id = Column(String(100), ForeignKey("experiments.experiment_id"), nullable=False, index=True)

    # Template content
    subject_line = Column(String(500))  # For email outreach
    body_template = Column(Text, nullable=False)  # Jinja2 template with {{variables}}

    # Personalization instructions for AI
    personalization_prompt = Column(Text)  # Instructions for Truefoundry agent

    # Channel configuration
    channel = Column(String(50), default="email")  # email, linkedin, slack, etc.

    # Template configuration
    config = Column(JSON)  # Additional settings (tone, length, CTA, etc.)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<OutreachTemplate {self.template_id}: {self.name} (experiment={self.experiment_id})>"
