import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from backend.app.fsm import AlertFSM, FSMState

@dataclass
class NormalizedEvent:
    event_id: str
    camera_id: int
    rule_id: int
    rule_name: str
    severity: str
    status: str
    timestamp: datetime
    details: str
    track_id: Optional[int] = None
    zone: Optional[str] = None

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "track_id": self.track_id,
            "zone": self.zone
        }

class EventManager:
    def __init__(self, debounce_seconds: int = 5, cooldown_seconds: int = 30, escalation_seconds: int = 60):
        self.fsm = AlertFSM(cooldown_seconds=cooldown_seconds)
        self.debounce_seconds = debounce_seconds
        self.escalation_seconds = escalation_seconds
        
        self.active_events: Dict[tuple[int, int], NormalizedEvent] = {}
        self.last_escalated: Dict[tuple[int, int], datetime] = {}
        
        self.rule_map = {
            "Counter Empty": 1,
            "Queue Count": 2,
            "Customer Wait": 3,
            "Late Opening": 4,
            "Crowd Congestion": 5,
            "Suspicious Unattended Bag": 6,
            "Entrance Blocked": 7,
            "Intrusion Detection": 8,
        }

    def _get_internal_rule_id(self, rule_name: str, track_id: Optional[int]) -> int:
        """
        Creates a unique rule ID for the FSM that incorporates the track_id if present.
        This allows track-specific cooldowns and state tracking (e.g., individual unattended bags).
        """
        base_id = self.rule_map.get(rule_name, 99)
        if track_id is not None:
            # Combine base rule ID and track ID safely for Python (arbitrary length)
            return int(f"{base_id}000{track_id}")
        return base_id

    def _escalate_severity(self, severity: str) -> str:
        levels = ["INFO", "WARNING", "HIGH", "CRITICAL"]
        try:
            idx = levels.index(severity.upper())
            if idx < len(levels) - 1:
                return levels[idx + 1]
        except ValueError:
            pass
        return severity

    def process_alerts(self, camera_id: int, alerts: List[Dict[str, Any]], now: Optional[datetime] = None) -> List[NormalizedEvent]:
        now = now or datetime.now()
        
        current_conditions = set()
        emitted_events = []
        
        # 1. Process active conditions reported by RuleEngine
        for alert in alerts:
            rule_name = alert["rule"]
            track_id = alert.get("track_id")
            internal_rule_id = self._get_internal_rule_id(rule_name, track_id)
            current_conditions.add(internal_rule_id)
            
            # Tick the FSM
            state = self.fsm.condition_detected(camera_id, internal_rule_id, now)
            key = (camera_id, internal_rule_id)
            
            if state.state == FSMState.MONITORING:
                # Apply Debounce
                if state.started_at and (now - state.started_at).total_seconds() >= self.debounce_seconds:
                    # Debounce threshold met, advance state to ALERT_SENT
                    state = self.fsm.send_alert(camera_id, internal_rule_id, now)
                    
                    event = NormalizedEvent(
                        event_id=str(uuid.uuid4()),
                        camera_id=camera_id,
                        rule_id=self.rule_map.get(rule_name, 99),
                        rule_name=rule_name,
                        severity=alert.get("severity", "INFO").upper(),
                        status=state.state.value,
                        timestamp=now,
                        details=alert.get("message", ""),
                        track_id=track_id,
                        zone=alert.get("zone")
                    )
                    
                    self.active_events[key] = event
                    self.last_escalated[key] = now
                    emitted_events.append(event)
                    
            elif state.state == FSMState.ALERT_SENT:
                # Check Escalation
                last_esc = self.last_escalated.get(key, state.started_at)
                if last_esc and (now - last_esc).total_seconds() >= self.escalation_seconds:
                    event = self.active_events.get(key)
                    if event:
                        new_sev = self._escalate_severity(event.severity)
                        if new_sev != event.severity:
                            # Create a copy so we don't accidentally mutate past events if we store them
                            event.severity = new_sev
                            event.timestamp = now
                            event.details = f"[ESCALATED] {event.details}"
                            self.last_escalated[key] = now
                            
                            emitted_events.append(NormalizedEvent(**event.__dict__))
                            
        # 2. Check for conditions that were active but are missing in the current frame
        keys_to_resolve = []
        for key in self.active_events.keys():
            cid, internal_rule_id = key
            if cid == camera_id and internal_rule_id not in current_conditions:
                keys_to_resolve.append(key)
                
        for key in keys_to_resolve:
            cid, internal_rule_id = key
            
            # Transition to RESOLVED
            state = self.fsm.resolve(cid, internal_rule_id, now)
            
            event = self.active_events[key]
            
            # Emit the RESOLVED state event so downstream consumers know it's over
            resolved_event = NormalizedEvent(**event.__dict__)
            resolved_event.status = state.state.value # RESOLVED
            resolved_event.timestamp = now
            emitted_events.append(resolved_event)
            
            # Immediately enter COOLDOWN phase after resolving
            self.fsm.start_cooldown(cid, internal_rule_id, now)
            
            # Cleanup active tracking
            del self.active_events[key]
            if key in self.last_escalated:
                del self.last_escalated[key]
                
        return emitted_events


def run_test():
    print("=" * 60)
    print("AURA SURVEILLANCE - EVENT MANAGER TEST")
    print("=" * 60)
    
    manager = EventManager(debounce_seconds=2, cooldown_seconds=5, escalation_seconds=3)
    camera_id = 1
    t0 = datetime.now()
    
    def print_events(events, time_offset):
        if not events:
            print(f"[T={time_offset}] No events emitted.")
        for e in events:
            print(f"[T={time_offset}] EMITTED: {e.status} | {e.rule_name} | {e.severity} | {e.details}")

    # 1. Debounce phase
    print("\n--- 1. Testing Debounce (Threshold: 2s) ---")
    alerts_in = [{"rule": "Crowd Congestion", "message": "15 people", "severity": "WARNING"}]
    
    events = manager.process_alerts(camera_id, alerts_in, t0)
    print_events(events, 0)
    
    t1 = t0 + timedelta(seconds=1)
    events = manager.process_alerts(camera_id, alerts_in, t1)
    print_events(events, 1)

    # 2. Alert generated
    print("\n--- 2. Testing Alert Generation ---")
    t2 = t0 + timedelta(seconds=2)
    events = manager.process_alerts(camera_id, alerts_in, t2)
    print_events(events, 2)

    # 3. Escalation
    print("\n--- 3. Testing Escalation (Threshold: 3s) ---")
    t3 = t0 + timedelta(seconds=6)
    events = manager.process_alerts(camera_id, alerts_in, t3)
    print_events(events, 6)

    # 4. Independent alerts
    print("\n--- 4. Testing Independent Alerts ---")
    alerts_in.append({"rule": "Suspicious Unattended Bag", "message": "Bag ID 10", "severity": "HIGH", "track_id": 10})
    t4 = t0 + timedelta(seconds=7)
    events = manager.process_alerts(camera_id, alerts_in, t4)
    print_events(events, 7)
    
    t5 = t0 + timedelta(seconds=9)
    events = manager.process_alerts(camera_id, alerts_in, t5)
    print_events(events, 9)

    # 5. Resolve
    print("\n--- 5. Testing Resolve ---")
    alerts_in = [{"rule": "Suspicious Unattended Bag", "message": "Bag ID 10", "severity": "HIGH", "track_id": 10}]
    t6 = t0 + timedelta(seconds=10)
    events = manager.process_alerts(camera_id, alerts_in, t6)
    print_events(events, 10)

    # 6. Cooldown works (suppresses duplicate)
    print("\n--- 6. Testing Cooldown Suppression (Threshold: 5s) ---")
    alerts_in.append({"rule": "Crowd Congestion", "message": "15 people", "severity": "WARNING"})
    t7 = t0 + timedelta(seconds=11)
    events = manager.process_alerts(camera_id, alerts_in, t7)
    print_events(events, 11)
    
    state = manager.fsm.get_state(camera_id, manager._get_internal_rule_id("Crowd Congestion", None))
    print(f"Internal FSM State for Crowd Congestion at T=11: {state.state.value}")

    # 7. Cooldown expires
    print("\n--- 7. Testing Cooldown Expiry ---")
    t8 = t0 + timedelta(seconds=16)
    events = manager.process_alerts(camera_id, alerts_in, t8)
    print_events(events, 16)
    
    t9 = t0 + timedelta(seconds=18)
    events = manager.process_alerts(camera_id, alerts_in, t9)
    print_events(events, 18)

    print("\n" + "=" * 60)
    print("EVENT MANAGER TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
