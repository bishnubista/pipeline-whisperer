"""
Experiments API routes for dashboard
"""
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.base import SessionLocal
from app.models.experiment import Experiment
from app.models.outreach_template import OutreachTemplate
from app.models.outreach_log import OutreachLog
from app.models.lead import Lead, LeadStatus


router = APIRouter(prefix="/experiments", tags=["experiments"])


# Pydantic models for responses
class ExperimentMetrics(BaseModel):
    experiment_id: str
    name: str
    variant: str
    is_active: bool

    # Thompson Sampling parameters
    alpha: float
    beta: float
    expected_conversion_rate: float

    # Performance metrics
    leads_assigned: int
    outreach_sent: int
    conversions: int
    conversion_rate: float
    responses_received: int

    # Timestamps
    created_at: datetime
    updated_at: datetime


class ExperimentUpdate(BaseModel):
    is_active: Optional[bool] = None


class DashboardOverview(BaseModel):
    total_leads: int
    scored_leads: int
    contacted_leads: int
    converted_leads: int

    active_experiments: int
    total_experiments: int

    best_performing_experiment: Optional[str]
    best_conversion_rate: float


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[ExperimentMetrics])
async def list_experiments(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all experiments with their performance metrics"""
    query = db.query(Experiment)

    if active_only:
        query = query.filter(Experiment.is_active == True)

    experiments = query.all()

    return [
        ExperimentMetrics(
            experiment_id=exp.experiment_id,
            name=exp.name,
            variant=exp.variant,
            is_active=exp.is_active,
            alpha=exp.alpha,
            beta=exp.beta,
            expected_conversion_rate=exp.alpha / (exp.alpha + exp.beta),
            leads_assigned=exp.leads_assigned or 0,
            outreach_sent=exp.outreach_sent or 0,
            conversions=exp.conversions or 0,
            conversion_rate=exp.conversion_rate or 0.0,
            responses_received=exp.responses_received or 0,
            created_at=exp.created_at,
            updated_at=exp.updated_at,
        )
        for exp in experiments
    ]


@router.get("/{experiment_id}", response_model=ExperimentMetrics)
async def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed metrics for a specific experiment"""
    exp = db.query(Experiment).filter(
        Experiment.experiment_id == experiment_id
    ).first()

    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return ExperimentMetrics(
        experiment_id=exp.experiment_id,
        name=exp.name,
        variant=exp.variant,
        is_active=exp.is_active,
        alpha=exp.alpha,
        beta=exp.beta,
        expected_conversion_rate=exp.alpha / (exp.alpha + exp.beta),
        leads_assigned=exp.leads_assigned or 0,
        outreach_sent=exp.outreach_sent or 0,
        conversions=exp.conversions or 0,
        conversion_rate=exp.conversion_rate or 0.0,
        responses_received=exp.responses_received or 0,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
    )


@router.patch("/{experiment_id}", response_model=ExperimentMetrics)
async def update_experiment(
    experiment_id: str,
    update: ExperimentUpdate,
    db: Session = Depends(get_db)
):
    """Update experiment (pause/activate)"""
    exp = db.query(Experiment).filter(
        Experiment.experiment_id == experiment_id
    ).first()

    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if update.is_active is not None:
        exp.is_active = update.is_active
        exp.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(exp)

    return ExperimentMetrics(
        experiment_id=exp.experiment_id,
        name=exp.name,
        variant=exp.variant,
        is_active=exp.is_active,
        alpha=exp.alpha,
        beta=exp.beta,
        expected_conversion_rate=exp.alpha / (exp.alpha + exp.beta),
        leads_assigned=exp.leads_assigned or 0,
        outreach_sent=exp.outreach_sent or 0,
        conversions=exp.conversions or 0,
        conversion_rate=exp.conversion_rate or 0.0,
        responses_received=exp.responses_received or 0,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
    )


@router.get("/overview/dashboard", response_model=DashboardOverview)
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """Get high-level overview metrics for dashboard"""

    # Lead counts
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    scored_leads = db.query(func.count(Lead.id)).filter(
        Lead.score.isnot(None)
    ).scalar() or 0
    contacted_leads = db.query(func.count(Lead.id)).filter(
        Lead.status == LeadStatus.CONTACTED
    ).scalar() or 0
    converted_leads = db.query(func.count(Lead.id)).filter(
        Lead.status == LeadStatus.CONVERTED
    ).scalar() or 0

    # Experiment counts
    total_experiments = db.query(func.count(Experiment.id)).scalar() or 0
    active_experiments = db.query(func.count(Experiment.id)).filter(
        Experiment.is_active == True
    ).scalar() or 0

    # Best performing experiment
    best_exp = db.query(Experiment).filter(
        Experiment.conversions > 0
    ).order_by(Experiment.conversion_rate.desc()).first()

    return DashboardOverview(
        total_leads=total_leads,
        scored_leads=scored_leads,
        contacted_leads=contacted_leads,
        converted_leads=converted_leads,
        active_experiments=active_experiments,
        total_experiments=total_experiments,
        best_performing_experiment=best_exp.experiment_id if best_exp else None,
        best_conversion_rate=best_exp.conversion_rate if best_exp else 0.0,
    )
