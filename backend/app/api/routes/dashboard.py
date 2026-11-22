from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import analytics, dashboard

router = APIRouter(tags=["dashboard", "analytics"])


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    return dashboard.dashboard_summary(db)


@router.get("/analytics/opportunities-over-time")
def opp_over_time(days: int = Query(14, ge=1, le=180), sport: str | None = None,
                  db: Session = Depends(get_db)):
    return analytics.opportunities_over_time(db, days, sport)


@router.get("/analytics/roi-distribution")
def roi_distribution(db: Session = Depends(get_db)):
    return analytics.roi_distribution(db)


@router.get("/analytics/roi-by-sport")
def roi_by_sport(db: Session = Depends(get_db)):
    return analytics.roi_by_sport(db)


@router.get("/analytics/roi-by-bookmaker")
def roi_by_bookmaker(db: Session = Depends(get_db)):
    return analytics.roi_by_bookmaker(db)


@router.get("/analytics/opportunity-lifetime")
def opportunity_lifetime(db: Session = Depends(get_db)):
    return analytics.opportunity_lifetime(db)


@router.get("/analytics/detected-vs-expired")
def detected_vs_expired(days: int = Query(14, ge=1, le=180),
                        db: Session = Depends(get_db)):
    return analytics.detected_vs_expired(db, days)


@router.get("/analytics/portfolio-curve")
def portfolio_curve(portfolio_id: str | None = None, db: Session = Depends(get_db)):
    return analytics.portfolio_curve(db, portfolio_id)
