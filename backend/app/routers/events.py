from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from ..database import get_db
from ..models import Event
from ..schemas import EventResponse, EventStatsResponse
from ..event_repository import EventRepository

repo = EventRepository()
SNAPSHOTS_DIR = Path("storage/snapshots").resolve()

router = APIRouter(
    prefix="/api/events",
    tags=["Events"],
)

@router.get("/stats", response_model=EventStatsResponse)
def get_event_stats(db: Session = Depends(get_db)):
    total_events = db.query(Event).count()
    active_events = db.query(Event).filter(Event.status.in_(["MONITORING", "ALERT_SENT"])).count()
    resolved_events = db.query(Event).filter(Event.status == "RESOLVED").count()
    
    # By severity
    severity_counts = {}
    for row in db.query(Event.severity).all():
        sev = row[0]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
    # By rule
    rule_counts = {}
    for row in db.query(Event.rule_name).all():
        r = row[0]
        if r:
            rule_counts[r] = rule_counts.get(r, 0) + 1
            
    return EventStatsResponse(
        total_events=total_events,
        active_events=active_events,
        resolved_events=resolved_events,
        by_severity=severity_counts,
        by_rule=rule_counts
    )


@router.get("/active", response_model=List[EventResponse])
def get_active_events(
    camera_id: Optional[int] = None,
):
    return repo.get_active_events(camera_id=camera_id)


@router.get("/", response_model=List[EventResponse])
def get_events(
    camera_id: Optional[int] = None,
    rule_id: Optional[int] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    return repo.get_events(
        limit=limit,
        offset=offset,
        camera_id=camera_id,
        rule_id=rule_id,
        severity=severity,
        status=status,
        start_time=start_time,
        end_time=end_time
    )


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str):
    event = repo.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}/resolve", response_model=EventResponse)
def resolve_event(event_id: str):
    event = repo.resolve_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
