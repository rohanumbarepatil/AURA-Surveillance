import time
from typing import List, Dict, Any

class RuleEngine:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = {
            "queue_threshold": 5,
            "wait_time_threshold": 300, # seconds
            "congestion_threshold": 15,
            "entrance_blocked_threshold": 3,
            "unattended_bag_threshold": 60, # seconds
            "intrusion_start_hour": 22,
            "intrusion_end_hour": 6,
            "opening_hour": 9,
        }
        if config:
            self.config.update(config)

        # State tracking
        self.track_states = {} # track_id -> {"zone": str, "entry_time": float, "last_seen": float}
        
    def evaluate(self, detections: List[Dict[str, Any]], timestamp: float = None) -> List[Dict[str, Any]]:
        """
        Evaluate rules based on current detections and state.
        detections: Output from ZoneEngine.process_detections
        timestamp: Current time (defaults to time.time())
        """
        if timestamp is None:
            timestamp = time.time()
            
        self._update_state(detections, timestamp)
        
        alerts = []
        alerts.extend(self._rule_counter_empty(detections, timestamp))
        alerts.extend(self._rule_queue_count(detections, timestamp))
        alerts.extend(self._rule_customer_wait(detections, timestamp))
        alerts.extend(self._rule_late_opening(detections, timestamp))
        alerts.extend(self._rule_crowd_congestion(detections, timestamp))
        alerts.extend(self._rule_unattended_bag(detections, timestamp))
        alerts.extend(self._rule_entrance_blocked(detections, timestamp))
        alerts.extend(self._rule_intrusion_detection(detections, timestamp))
        
        return alerts

    def _update_state(self, detections: List[Dict[str, Any]], timestamp: float):
        current_tracks = set()
        
        for det in detections:
            track_id = det.get("track_id")
            zone = det.get("zone")
            
            if track_id is not None:
                current_tracks.add(track_id)
                if track_id not in self.track_states:
                    self.track_states[track_id] = {
                        "zone": zone,
                        "entry_time": timestamp,
                        "last_seen": timestamp
                    }
                else:
                    state = self.track_states[track_id]
                    state["last_seen"] = timestamp
                    if state["zone"] != zone:
                        # Zone changed
                        state["zone"] = zone
                        state["entry_time"] = timestamp
                        
        # Basic cleanup: remove tracks not seen for a while (e.g., 60 seconds)
        # to prevent memory leaks in long-running processes
        to_remove = []
        for tid, state in self.track_states.items():
            if timestamp - state["last_seen"] > 60:
                to_remove.append(tid)
        for tid in to_remove:
            del self.track_states[tid]

    def _get_zone_counts(self, detections: List[Dict[str, Any]], class_name: str = "person") -> Dict[str, int]:
        counts = {}
        for det in detections:
            if det.get("class_name") == class_name and det.get("zone"):
                z = det["zone"]
                counts[z] = counts.get(z, 0) + 1
        return counts

    # 1. Counter Empty
    def _rule_counter_empty(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        counts = self._get_zone_counts(detections, "person")
        if counts.get("Cash Counter", 0) == 0:
            return [{
                "rule": "Counter Empty",
                "message": "No staff detected at the Cash Counter.",
                "severity": "medium"
            }]
        return []

    # 2. Queue Count
    def _rule_queue_count(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        counts = self._get_zone_counts(detections, "person")
        q_count = counts.get("Queue Corridor", 0)
        if q_count > self.config["queue_threshold"]:
            return [{
                "rule": "Queue Count",
                "message": f"High queue count: {q_count} people.",
                "severity": "medium"
            }]
        return []

    # 3. Customer Wait
    def _rule_customer_wait(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        alerts = []
        for det in detections:
            if det.get("class_name") == "person" and det.get("zone") == "Customer Waiting Lounge":
                track_id = det.get("track_id")
                state = self.track_states.get(track_id)
                if state and state["zone"] == "Customer Waiting Lounge":
                    wait_time = timestamp - state["entry_time"]
                    if wait_time > self.config["wait_time_threshold"]:
                        alerts.append({
                            "rule": "Customer Wait",
                            "message": f"Customer {track_id} waiting too long ({int(wait_time)}s).",
                            "severity": "low",
                            "track_id": track_id
                        })
        return alerts

    # 4. Late Opening
    def _rule_late_opening(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        current_hour = time.localtime(timestamp).tm_hour
        opening_hour = self.config["opening_hour"]
        
        # Check if we are in the first hour of opening and counter is empty
        if opening_hour <= current_hour < opening_hour + 1:
            counts = self._get_zone_counts(detections, "person")
            if counts.get("Cash Counter", 0) == 0:
                return [{
                    "rule": "Late Opening",
                    "message": "Cash counter is empty after opening hours.",
                    "severity": "high"
                }]
        return []

    # 5. Crowd Congestion
    def _rule_crowd_congestion(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        total_people = sum(1 for d in detections if d.get("class_name") == "person")
        if total_people > self.config["congestion_threshold"]:
            return [{
                "rule": "Crowd Congestion",
                "message": f"High crowd congestion detected: {total_people} people.",
                "severity": "high"
            }]
        return []

    # 6. Suspicious Unattended Bag
    def _rule_unattended_bag(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        alerts = []
        bag_classes = {"backpack", "suitcase", "handbag"}
        for det in detections:
            if det.get("class_name") in bag_classes:
                track_id = det.get("track_id")
                state = self.track_states.get(track_id)
                if state:
                    duration = timestamp - state["entry_time"]
                    if duration > self.config["unattended_bag_threshold"]:
                        alerts.append({
                            "rule": "Suspicious Unattended Bag",
                            "message": f"Unattended {det.get('class_name')} detected (ID: {track_id}).",
                            "severity": "critical",
                            "track_id": track_id
                        })
        return alerts

    # 7. Entrance Blocked
    def _rule_entrance_blocked(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        counts = self._get_zone_counts(detections, "person")
        entrance_count = counts.get("Main Entrance", 0)
        if entrance_count > self.config["entrance_blocked_threshold"]:
            return [{
                "rule": "Entrance Blocked",
                "message": f"Main entrance is blocked by {entrance_count} people.",
                "severity": "high"
            }]
        return []

    # 8. Intrusion Detection
    def _rule_intrusion_detection(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Dict[str, Any]]:
        current_hour = time.localtime(timestamp).tm_hour
        start_h = self.config["intrusion_start_hour"]
        end_h = self.config["intrusion_end_hour"]
        
        is_intrusion_time = False
        if start_h > end_h: # e.g. 22 to 6
            if current_hour >= start_h or current_hour < end_h:
                is_intrusion_time = True
        else:
            if start_h <= current_hour < end_h:
                is_intrusion_time = True
                
        if is_intrusion_time:
            total_people = sum(1 for d in detections if d.get("class_name") == "person")
            if total_people > 0:
                return [{
                    "rule": "Intrusion Detection",
                    "message": f"Intrusion detected! {total_people} people present during restricted hours.",
                    "severity": "critical"
                }]
        return []


def run_test():
    print("=" * 60)
    print("AURA SURVEILLANCE - RULE ENGINE TEST")
    print("=" * 60)
    
    engine = RuleEngine()
    
    # Simulate some detections
    # Using the format expected from ZoneEngine.process_detections
    test_detections_1 = [
        {"track_id": 1, "class_id": 0, "class_name": "person", "confidence": 0.9, "bbox": [0,0,10,10], "center": [5,5], "zone": "Queue Corridor"},
        {"track_id": 2, "class_id": 0, "class_name": "person", "confidence": 0.9, "bbox": [0,0,10,10], "center": [5,5], "zone": "Queue Corridor"},
        {"track_id": 3, "class_id": 0, "class_name": "person", "confidence": 0.9, "bbox": [0,0,10,10], "center": [5,5], "zone": "Queue Corridor"},
        {"track_id": 4, "class_id": 0, "class_name": "person", "confidence": 0.9, "bbox": [0,0,10,10], "center": [5,5], "zone": "Queue Corridor"},
        {"track_id": 5, "class_id": 0, "class_name": "person", "confidence": 0.9, "bbox": [0,0,10,10], "center": [5,5], "zone": "Queue Corridor"},
        {"track_id": 6, "class_id": 0, "class_name": "person", "confidence": 0.9, "bbox": [0,0,10,10], "center": [5,5], "zone": "Queue Corridor"},
        
        {"track_id": 10, "class_id": 24, "class_name": "backpack", "confidence": 0.9, "bbox": [0,0,10,10], "center": [5,5], "zone": "Customer Waiting Lounge"},
    ]
    
    print("\nProcessing Frame 1 (T=0s)...")
    base_time = time.time()
    alerts = engine.evaluate(test_detections_1, timestamp=base_time)
    for a in alerts:
        print(f"[{a['severity'].upper()}] {a['rule']}: {a['message']}")
        
    print("\nProcessing Frame 2 (T=70s)...")
    # Simulate time passing > 60s for unattended bag, and queue still > 5
    alerts = engine.evaluate(test_detections_1, timestamp=base_time + 70.0)
    for a in alerts:
        print(f"[{a['severity'].upper()}] {a['rule']}: {a['message']}")

    print("-" * 60)
    print("Rule Engine test completed.")

if __name__ == "__main__":
    run_test()
