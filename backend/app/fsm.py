from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


class FSMState(str, Enum):
    NORMAL = "NORMAL"
    MONITORING = "MONITORING"
    ALERT_SENT = "ALERT_SENT"
    RESOLVED = "RESOLVED"
    COOLDOWN = "COOLDOWN"


@dataclass
class EventState:
    camera_id: int
    rule_id: int
    state: FSMState = FSMState.NORMAL
    started_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None


class AlertFSM:
    """
    Alert lifecycle state machine.

    NORMAL
        ↓ condition detected
    MONITORING
        ↓ threshold reached
    ALERT_SENT
        ↓ condition resolved
    RESOLVED
        ↓ cooldown completed
    COOLDOWN
        ↓
    NORMAL
    """

    def __init__(self, cooldown_seconds: int = 30):
        self.cooldown_seconds = cooldown_seconds
        self.states: dict[tuple[int, int], EventState] = {}

    def _key(self, camera_id: int, rule_id: int) -> tuple[int, int]:
        return camera_id, rule_id

    def get_state(self, camera_id: int, rule_id: int) -> EventState:
        key = self._key(camera_id, rule_id)

        if key not in self.states:
            self.states[key] = EventState(
                camera_id=camera_id,
                rule_id=rule_id,
            )

        return self.states[key]

    def condition_detected(
        self,
        camera_id: int,
        rule_id: int,
        now: Optional[datetime] = None,
    ) -> EventState:

        now = now or datetime.now()
        event = self.get_state(camera_id, rule_id)

        # Cooldown still active
        if event.state == FSMState.COOLDOWN:
            if event.cooldown_until and now < event.cooldown_until:
                return event

            # Cooldown finished
            event.state = FSMState.NORMAL
            event.cooldown_until = None

        # NORMAL → MONITORING
        if event.state == FSMState.NORMAL:
            event.state = FSMState.MONITORING
            event.started_at = now

        # Update last detection
        event.last_seen_at = now

        return event

    def send_alert(
        self,
        camera_id: int,
        rule_id: int,
        now: Optional[datetime] = None,
    ) -> EventState:

        now = now or datetime.now()
        event = self.get_state(camera_id, rule_id)

        # MONITORING → ALERT_SENT
        if event.state == FSMState.MONITORING:
            event.state = FSMState.ALERT_SENT

        event.last_seen_at = now

        return event

    def resolve(
        self,
        camera_id: int,
        rule_id: int,
        now: Optional[datetime] = None,
    ) -> EventState:

        now = now or datetime.now()
        event = self.get_state(camera_id, rule_id)

        # ALERT_SENT → RESOLVED
        if event.state == FSMState.ALERT_SENT:
            event.state = FSMState.RESOLVED
            event.last_seen_at = now

        return event

    def start_cooldown(
        self,
        camera_id: int,
        rule_id: int,
        now: Optional[datetime] = None,
    ) -> EventState:

        now = now or datetime.now()
        event = self.get_state(camera_id, rule_id)

        # RESOLVED → COOLDOWN
        if event.state == FSMState.RESOLVED:
            event.state = FSMState.COOLDOWN
            event.cooldown_until = now + timedelta(
                seconds=self.cooldown_seconds
            )

        return event

    def reset(
        self,
        camera_id: int,
        rule_id: int,
    ) -> EventState:

        event = self.get_state(camera_id, rule_id)

        event.state = FSMState.NORMAL
        event.started_at = None
        event.last_seen_at = None
        event.cooldown_until = None

        return event


def run_test():
    print("=" * 60)
    print("AURA SURVEILLANCE - FSM TEST")
    print("=" * 60)

    fsm = AlertFSM(cooldown_seconds=30)

    camera_id = 1
    rule_id = 8

    t0 = datetime.now()

    print("\n1. Initial state")
    event = fsm.get_state(camera_id, rule_id)
    print("State:", event.state.value)

    print("\n2. Condition detected")
    event = fsm.condition_detected(
        camera_id,
        rule_id,
        t0,
    )
    print("State:", event.state.value)

    print("\n3. Threshold reached → Alert")
    event = fsm.send_alert(
        camera_id,
        rule_id,
        t0,
    )
    print("State:", event.state.value)

    print("\n4. Operator resolves event")
    event = fsm.resolve(
        camera_id,
        rule_id,
        t0,
    )
    print("State:", event.state.value)

    print("\n5. Start cooldown")
    event = fsm.start_cooldown(
        camera_id,
        rule_id,
        t0,
    )
    print("State:", event.state.value)
    print("Cooldown until:", event.cooldown_until)

    print("\n6. Reset after cooldown")
    t1 = t0 + timedelta(seconds=31)

    event = fsm.condition_detected(
        camera_id,
        rule_id,
        t1,
    )

    print("State:", event.state.value)

    print("\n" + "=" * 60)
    print("FSM TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_test()