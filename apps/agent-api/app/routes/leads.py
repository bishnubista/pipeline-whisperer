"""Lead management API endpoints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.models.base import get_db
from app.models.lead import Lead, LeadStatus, LeadPersona

router = APIRouter(prefix="/leads", tags=["leads"])


# Pydantic schemas for responses
class LeadResponse(BaseModel):
    id: int
    lightfield_id: str
    company_name: str
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_title: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    score: Optional[float]
    persona: LeadPersona
    status: LeadStatus
    created_at: datetime
    scored_at: Optional[datetime]

    class Config:
        from_attributes = True


class LeadDetailResponse(LeadResponse):
    website: Optional[str]
    raw_payload: dict
    scoring_metadata: Optional[dict]
    experiment_id: Optional[str]
    outreach_count: int
    response_count: int
    contacted_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class LeadStatsResponse(BaseModel):
    total_leads: int
    by_status: dict
    by_persona: dict
    avg_score: float
    top_industries: List[dict]


@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    status: Optional[LeadStatus] = None,
    persona: Optional[LeadPersona] = None,
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List leads with optional filtering

    - **status**: Filter by lead status
    - **persona**: Filter by lead persona
    - **min_score**: Minimum score threshold
    - **limit**: Maximum number of results (max 200)
    - **offset**: Pagination offset
    """
    query = db.query(Lead)

    # Apply filters
    if status:
        query = query.filter(Lead.status == status)
    if persona:
        query = query.filter(Lead.persona == persona)
    if min_score is not None:
        query = query.filter(Lead.score >= min_score)

    # Order by score descending, then created_at
    query = query.order_by(Lead.score.desc(), Lead.created_at.desc())

    # Paginate
    leads = query.offset(offset).limit(limit).all()

    return leads


@router.get("/stats", response_model=LeadStatsResponse)
async def get_lead_stats(db: Session = Depends(get_db)):
    """Get aggregate statistics about leads"""
    from sqlalchemy import func

    total_leads = db.query(func.count(Lead.id)).scalar()

    # Count by status
    status_counts = db.query(
        Lead.status, func.count(Lead.id)
    ).group_by(Lead.status).all()
    by_status = {status.value: count for status, count in status_counts}

    # Count by persona
    persona_counts = db.query(
        Lead.persona, func.count(Lead.id)
    ).group_by(Lead.persona).all()
    by_persona = {persona.value: count for persona, count in persona_counts}

    # Average score
    avg_score = db.query(func.avg(Lead.score)).scalar() or 0.0

    # Top industries
    industry_counts = db.query(
        Lead.industry, func.count(Lead.id)
    ).group_by(Lead.industry).order_by(func.count(Lead.id).desc()).limit(5).all()
    top_industries = [
        {"industry": industry, "count": count}
        for industry, count in industry_counts if industry
    ]

    return LeadStatsResponse(
        total_leads=total_leads,
        by_status=by_status,
        by_persona=by_persona,
        avg_score=round(avg_score, 3),
        top_industries=top_industries
    )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.get("/lightfield/{lightfield_id}", response_model=LeadDetailResponse)
async def get_lead_by_lightfield_id(lightfield_id: str, db: Session = Depends(get_db)):
    """Get lead by Lightfield CRM ID"""
    lead = db.query(Lead).filter(Lead.lightfield_id == lightfield_id).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead
