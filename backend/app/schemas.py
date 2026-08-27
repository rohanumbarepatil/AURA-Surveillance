from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CameraCreate(BaseModel):
    name: str
    source: str
    source_type: str = "VIDEO"


class CameraUpdate(BaseModel):
    name: str | None = None
    source: str | None = None
    source_type: str | None = None
    enabled: bool | None = None


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source: str
    source_type: str
    status: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    camera_id: int
    rule_id: int
    rule_name: str | None
    severity: str
    status: str
    timestamp: datetime
    created_at: datetime
    details: str
    snapshot_path: str | None = None
    track_id: int | None = None
    zone: str | None = None
    resolved_at: datetime | None = None


class EventStatsResponse(BaseModel):
    total_events: int
    active_events: int
    resolved_events: int
    by_severity: dict[str, int]
    by_rule: dict[str, int]