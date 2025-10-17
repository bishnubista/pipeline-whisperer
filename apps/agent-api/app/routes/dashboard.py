"""
Dashboard API routes - timeline, activity feed, real-time metrics
"""
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.base import SessionLocal
from app.models.lead import Lead, LeadStatus
from app.models.experiment import Experiment
from app.models.outreach_log import OutreachLog, OutreachStatus


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class LeadTimelineItem(BaseModel):
    id: int
    lightfield_id: str
    company_name: str
    contact_name: Optional[str]
    status: str
    score: Optional[float]
    experiment_id: Optional[str]
    created_at: datetime
    scored_at: Optional[datetime]
    contacted_at: Optional[datetime]


class ActivityItem(BaseModel):
    timestamp: datetime
    event_type: str
    description: str
    lead_id: Optional[int]
    experiment_id: Optional[str]
    metadata: Optional[dict]


class PipelineMetrics(BaseModel):
    """Real-time pipeline metrics"""
    # Funnel stages
    leads_raw: int
    leads_scored: int
    leads_contacted: int
    leads_responded: int
    leads_converted: int

    # Today's activity
    new_leads_today: int
    outreach_sent_today: int
    conversions_today: int

    # Conversion rates
    score_to_contact_rate: float
    contact_to_conversion_rate: float
    overall_conversion_rate: float


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/timeline", response_model=List[LeadTimelineItem])
async def get_lead_timeline(
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get recent leads with their pipeline progress"""
    query = db.query(Lead).order_by(desc(Lead.created_at))

    if status:
        query = query.filter(Lead.status == status)

    leads = query.limit(limit).all()

    return [
        LeadTimelineItem(
            id=lead.id,
            lightfield_id=lead.lightfield_id,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            status=lead.status.value,
            score=lead.score,
            experiment_id=lead.experiment_id,
            created_at=lead.created_at,
            scored_at=lead.scored_at,
            contacted_at=lead.contacted_at,
        )
        for lead in leads
    ]


@router.get("/activity", response_model=List[ActivityItem])
async def get_activity_feed(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get recent activity feed (leads + outreach events)"""
    activities = []

    # Recent leads
    recent_leads = db.query(Lead).order_by(desc(Lead.created_at)).limit(limit // 2).all()
    for lead in recent_leads:
        activities.append(ActivityItem(
            timestamp=lead.created_at,
            event_type="lead.created",
            description=f"New lead: {lead.company_name}",
            lead_id=lead.id,
            experiment_id=None,
            metadata={
                "company": lead.company_name,
                "industry": lead.industry,
            }
        ))

        if lead.scored_at:
            activities.append(ActivityItem(
                timestamp=lead.scored_at,
                event_type="lead.scored",
                description=f"{lead.company_name} scored {lead.score:.2f}",
                lead_id=lead.id,
                experiment_id=None,
                metadata={
                    "score": lead.score,
                    "persona": lead.persona,
                }
            ))

        if lead.contacted_at and lead.experiment_id:
            activities.append(ActivityItem(
                timestamp=lead.contacted_at,
                event_type="outreach.sent",
                description=f"Outreach sent to {lead.company_name}",
                lead_id=lead.id,
                experiment_id=lead.experiment_id,
                metadata={
                    "experiment": lead.experiment_id,
                }
            ))

        if lead.status == LeadStatus.CONVERTED:
            activities.append(ActivityItem(
                timestamp=lead.updated_at,
                event_type="lead.converted",
                description=f"🎉 {lead.company_name} converted!",
                lead_id=lead.id,
                experiment_id=lead.experiment_id,
                metadata={
                    "experiment": lead.experiment_id,
                }
            ))

    # Sort by timestamp descending
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    return activities[:limit]


@router.get("/metrics", response_model=PipelineMetrics)
async def get_pipeline_metrics(db: Session = Depends(get_db)):
    """Get real-time pipeline metrics"""

    # Funnel stages
    leads_raw = db.query(func.count(Lead.id)).scalar() or 0
    leads_scored = db.query(func.count(Lead.id)).filter(
        Lead.score.isnot(None)
    ).scalar() or 0
    leads_contacted = db.query(func.count(Lead.id)).filter(
        Lead.status == LeadStatus.CONTACTED
    ).scalar() or 0
    leads_responded = db.query(func.count(Lead.id)).filter(
        Lead.status == LeadStatus.RESPONDED
    ).scalar() or 0
    leads_converted = db.query(func.count(Lead.id)).filter(
        Lead.status == LeadStatus.CONVERTED
    ).scalar() or 0

    # Today's activity
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    new_leads_today = db.query(func.count(Lead.id)).filter(
        Lead.created_at >= today
    ).scalar() or 0
    outreach_sent_today = db.query(func.count(Lead.id)).filter(
        Lead.contacted_at >= today
    ).scalar() or 0
    conversions_today = db.query(func.count(Lead.id)).filter(
        Lead.status == LeadStatus.CONVERTED,
        Lead.updated_at >= today
    ).scalar() or 0

    # Conversion rates
    score_to_contact_rate = (leads_contacted / leads_scored * 100) if leads_scored > 0 else 0.0
    contact_to_conversion_rate = (leads_converted / leads_contacted * 100) if leads_contacted > 0 else 0.0
    overall_conversion_rate = (leads_converted / leads_raw * 100) if leads_raw > 0 else 0.0

    return PipelineMetrics(
        leads_raw=leads_raw,
        leads_scored=leads_scored,
        leads_contacted=leads_contacted,
        leads_responded=leads_responded,
        leads_converted=leads_converted,
        new_leads_today=new_leads_today,
        outreach_sent_today=outreach_sent_today,
        conversions_today=conversions_today,
        score_to_contact_rate=round(score_to_contact_rate, 1),
        contact_to_conversion_rate=round(contact_to_conversion_rate, 1),
        overall_conversion_rate=round(overall_conversion_rate, 1),
    )
