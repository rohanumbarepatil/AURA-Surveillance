import time
from datetime import datetime
import numpy as np

from backend.app.zone_engine import ZoneEngine, Detection
from backend.app.rule_engine import RuleEngine
from backend.app.event_manager import EventManager
from backend.app.snapshot_manager import SnapshotManager
from backend.app.event_repository import EventRepository
from backend.app.websocket_manager import manager as ws_manager


class SandboxPipeline:
    """
    Orchestrates the AI pipeline for the Demo Sandbox.
    Connects: YOLO Detections → ZoneEngine → RuleEngine → EventManager → SnapshotManager → EventRepository → WebSocket
    """
    
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        self.zone_engine = None
        self.rule_engine = RuleEngine()
        self.event_manager = EventManager()
        self.snapshot_manager = SnapshotManager()
        self.event_repository = EventRepository()
        self.total_events_generated = 0
        
    def initialize(self, width: int, height: int, fps: float):
        """Called by video_processor when video is opened."""
        self.zone_engine = ZoneEngine(width, height)
        
    def process_frame(self, frame: np.ndarray, timestamp: float, detections_data: list) -> list:
        """Called by video_processor per frame with YOLO detections."""
        if not self.zone_engine:
            return []
            
        # 1. Convert to ZoneEngine Detections
        detections = []
        for det in detections_data:
            detections.append(Detection(
                track_id=int(det["track_id"]),
                class_id=int(det["class_id"]),
                class_name="person", # Hardcoded for now based on class 0
                confidence=float(det["confidence"]),
                x1=int(det["x1"]),
                y1=int(det["y1"]),
                x2=int(det["x2"]),
                y2=int(det["y2"])
            ))
            
        # 2. Zone Engine
        zoned_results = self.zone_engine.process_detections(detections)
        
        # Draw zone names on frame (optional enhancement, but useful for Demo Sandbox playback)
        import cv2
        for result in zoned_results:
            if result.get("zone"):
                x1 = int(result["bbox"][0])
                y2 = int(result["bbox"][3])
                cv2.putText(
                    frame,
                    f"[{result['zone']}]",
                    (x1, y2 + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 0),
                    1,
                    cv2.LINE_AA
                )
        
        # 3. Rule Engine
        alerts = self.rule_engine.evaluate(zoned_results, timestamp)
        
        # 4. Event Manager
        now_dt = datetime.fromtimestamp(timestamp)
        events = self.event_manager.process_alerts(self.camera_id, alerts, now_dt)
        
        # 5. Handle Events
        for event in events:
            # We only count new actual alert transitions, not RESOLVED, for the sandbox stats
            if event.status == "ALERT_SENT":
                self.total_events_generated += 1
                
            # Snapshot
            snapshot_path = self.snapshot_manager.save_snapshot(frame, event)
            
            # Database Persistence
            self.event_repository.create_event(event, snapshot_path)
            
            # WebSocket Broadcast
            ws_manager.broadcast_event_sync(event)
            
        return events
