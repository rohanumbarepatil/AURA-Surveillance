import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, engine, Base
from backend.app.models import Event
from backend.app.event_manager import NormalizedEvent


class EventRepository:
    def __init__(self):
        self._ensure_schema_updated()

   def _ensure_schema_updated(self):
        """
        Dynamically adds missing columns if the table was created before the schema update,
        and creates necessary indexes without destroying existing data.
        """
            # Check existing columns using SQLite pragma
          Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
            
            # Map of column to schema definition for missing columns
            updates = {
                "event_id": "VARCHAR(36)",
                "rule_name": "VARCHAR(150)",
                "zone": "VARCHAR(100)",
                "created_at": "DATETIME",
                "snapshot_path": "VARCHAR(500)"
            }
            
            for col, col_type in updates.items():
                if col not in columns:
                    # Parameterized ALTER TABLE is not supported by SQLite, but these are safe hardcoded strings
                    conn.execute(text(f"ALTER TABLE events ADD COLUMN {col} {col_type}"))
            
            # Create indexes for commonly queried fields
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_events_event_id ON events (event_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_camera_id ON events (camera_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_rule_id ON events (rule_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_status ON events (status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_timestamp ON events (timestamp)"))

    def create_event(self, event: NormalizedEvent, snapshot_path: Optional[str] = None) -> Event:
        with SessionLocal() as db:
            # Handle duplicate event_id safely
            existing = db.query(Event).filter(Event.event_id == event.event_id).first()
            if existing:
                return existing
                
            db_event = Event(
                event_id=event.event_id,
                camera_id=event.camera_id,
                rule_id=event.rule_id,
                rule_name=event.rule_name,
                severity=event.severity,
                status=event.status,
                timestamp=event.timestamp,
                created_at=datetime.utcnow(),
                details=event.details,
                track_id=event.track_id,
                zone=event.zone,
                snapshot_path=snapshot_path,
                snapshot=snapshot_path # Maintained for backward compatibility
            )
            db.add(db_event)
            db.commit()
            db.refresh(db_event)
            return db_event

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        with SessionLocal() as db:
            return db.query(Event).filter(Event.event_id == event_id).first()

    def get_events(
        self, 
        limit: int = 100, 
        offset: int = 0, 
        camera_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Event]:
        with SessionLocal() as db:
            query = db.query(Event)
            
            if camera_id is not None:
                query = query.filter(Event.camera_id == camera_id)
            if rule_id is not None:
                query = query.filter(Event.rule_id == rule_id)
            if severity is not None:
                query = query.filter(Event.severity == severity)
            if status is not None:
                query = query.filter(Event.status == status)
            if start_time is not None:
                query = query.filter(Event.timestamp >= start_time)
            if end_time is not None:
                query = query.filter(Event.timestamp <= end_time)
                
            return query.order_by(Event.timestamp.desc()).limit(limit).offset(offset).all()

    def get_active_events(self, camera_id: Optional[int] = None) -> List[Event]:
        """Returns events that are actively being monitored or alerting."""
        with SessionLocal() as db:
            query = db.query(Event).filter(Event.status.in_(["MONITORING", "ALERT_SENT"]))
            if camera_id is not None:
                query = query.filter(Event.camera_id == camera_id)
            return query.order_by(Event.timestamp.desc()).all()

    def get_events_by_camera(self, camera_id: int, limit: int = 100) -> List[Event]:
        return self.get_events(camera_id=camera_id, limit=limit)

    def get_events_by_rule(self, rule_id: int, limit: int = 100) -> List[Event]:
        return self.get_events(rule_id=rule_id, limit=limit)

    def update_event_status(
        self, 
        event_id: str, 
        new_status: str, 
        new_severity: Optional[str] = None, 
        details_append: Optional[str] = None
    ) -> Optional[Event]:
        with SessionLocal() as db:
            db_event = db.query(Event).filter(Event.event_id == event_id).first()
            if not db_event:
                return None
                
            db_event.status = new_status
            if new_severity:
                db_event.severity = new_severity
            if details_append:
                db_event.details = f"{db_event.details} | {details_append}"
                
            db.commit()
            db.refresh(db_event)
            return db_event

    def resolve_event(self, event_id: str) -> Optional[Event]:
        with SessionLocal() as db:
            db_event = db.query(Event).filter(Event.event_id == event_id).first()
            if not db_event:
                return None
                
            db_event.status = "RESOLVED"
            db_event.resolved_at = datetime.utcnow()
            
            db.commit()
            db.refresh(db_event)
            return db_event


def run_test():
    print("=" * 60)
    print("AURA SURVEILLANCE - EVENT REPOSITORY TEST")
    print("=" * 60)
    
    # 1. Initialize Database / Repository
    print("\\n--- 1. Initializing Database ---")
    # In case the table doesn't exist at all, we call init_db
    from backend.app.database import init_db
    init_db()
    
    repo = EventRepository()
    print("Schema verified and indexes created.")
    
    # 2. Create sample NormalizedEvent
    print("\\n--- 2. Creating Sample Event ---")
    event_uuid = str(uuid.uuid4())
    norm_event = NormalizedEvent(
        event_id=event_uuid,
        camera_id=999,
        rule_id=5,
        rule_name="Crowd Congestion",
        severity="WARNING",
        status="ALERT_SENT",
        timestamp=datetime.utcnow(),
        details="20 people detected in main lobby",
        track_id=None,
        zone="Main Entrance"
    )
    
    # 3. Insert event
    print("\\n--- 3. Inserting Event ---")
    snapshot_path = f"storage/snapshots/999/2026-08-28/test_{event_uuid}.jpg"
    created = repo.create_event(norm_event, snapshot_path=snapshot_path)
    print(f"Created DB Event: ID={created.id}, Event_ID={created.event_id}, Status={created.status}")
    
    # 4. Verify duplicate protection
    print("\\n--- 4. Testing Duplicate Protection ---")
    duplicate = repo.create_event(norm_event, snapshot_path=snapshot_path)
    print(f"Duplicate call returned existing DB Event ID: {duplicate.id}")
    assert duplicate.id == created.id, "Duplicate protection failed!"
    
    # 5. Retrieve by event_id
    print("\\n--- 5. Retrieving by Event ID ---")
    retrieved = repo.get_event_by_id(event_uuid)
    print(f"Retrieved: Rule={retrieved.rule_name}, Zone={retrieved.zone}, Snapshot={retrieved.snapshot_path}")
    
    # 6. Retrieve list / filter by camera / severity
    print("\\n--- 6. Filtering and Pagination ---")
    cam_events = repo.get_events(camera_id=999, severity="WARNING", limit=10, offset=0)
    print(f"Events for Camera 999 with WARNING severity: {len(cam_events)}")
    
    # 7. Update status
    print("\\n--- 7. Updating Status ---")
    updated = repo.update_event_status(
        event_id=event_uuid,
        new_status="ALERT_SENT",
        new_severity="CRITICAL",
        details_append="ESCALATED: 30 people now"
    )
    print(f"Updated Event: Severity={updated.severity}, Details={updated.details}")
    
    # 8. Resolve event
    print("\\n--- 8. Resolving Event ---")
    resolved = repo.resolve_event(event_uuid)
    print(f"Resolved Event: Status={resolved.status}, Resolved_At={resolved.resolved_at}")
    
    # Check active events (should not include the resolved one)
    active = repo.get_active_events(camera_id=999)
    print(f"Active Events for Camera 999: {len(active)} (Expected: 0 if only this one exists)")

    print("\\n" + "=" * 60)
    print("EVENT REPOSITORY TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
