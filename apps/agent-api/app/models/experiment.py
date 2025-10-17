"""Experiment model - tracks A/B tests and learning iterations"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from .base import Base


class Experiment(Base):
    """Experiment tracking for A/B testing outreach strategies"""
    __tablename__ = "experiments"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Experiment metadata
    experiment_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))

    # Experiment configuration
    variant = Column(String(50))  # e.g., "control", "variant_a", "variant_b"
    config = Column(JSON)  # Experiment-specific settings (templates, timing, etc.)

    # Performance metrics
    leads_assigned = Column(Integer, default=0)
    outreach_sent = Column(Integer, default=0)
    responses_received = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    # Calculated performance
    conversion_rate = Column(Float, default=0.0)  # conversions / leads_assigned
    response_rate = Column(Float, default=0.0)  # responses / outreach_sent

    # Thompson Sampling priors (for multi-armed bandit)
    alpha = Column(Float, default=1.0)  # Successes prior
    beta = Column(Float, default=1.0)  # Failures prior

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    ended_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Experiment {self.experiment_id}: {self.name} ({self.conversion_rate:.2%})>"

    def update_metrics(self):
        """Recalculate performance metrics"""
        if self.leads_assigned > 0:
            self.conversion_rate = self.conversions / self.leads_assigned
        if self.outreach_sent > 0:
            self.response_rate = self.responses_received / self.outreach_sent
