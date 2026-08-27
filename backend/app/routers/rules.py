from fastapi import APIRouter
from typing import List

from ..schemas import EventResponse
from ..event_repository import EventRepository

repo = EventRepository()

router = APIRouter(
    prefix="/api/rules",
    tags=["Rules"],
)

@router.get("/{rule_id}/events", response_model=List[EventResponse])
def get_rule_events(
    rule_id: int,
    limit: int = 100,
):
    return repo.get_events_by_rule(rule_id, limit=limit)
