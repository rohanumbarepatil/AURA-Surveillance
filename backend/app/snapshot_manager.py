import os
import cv2
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np

from backend.app.event_manager import NormalizedEvent

class SnapshotManager:
    """
    Manages saving, retrieving, and cleaning up CCTV alert snapshots.
    Organizes files as: {base_dir}/{camera_id}/{date}/{time}_{rule_name}_{event_id}.jpg
    """
    
    def __init__(self, base_dir: str = "storage/snapshots"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_date_str(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")
        
    def _get_time_str(self, dt: datetime) -> str:
        return dt.strftime("%H%M%S")
        
    def _build_path(self, event: NormalizedEvent) -> Path:
        date_str = self._get_date_str(event.timestamp)
        # Clean rule name for filename
        clean_rule = event.rule_name.replace(" ", "_").lower()
        time_str = self._get_time_str(event.timestamp)
        
        # storage/snapshots/{camera_id}/{date}/
        dir_path = self.base_dir / str(event.camera_id) / date_str
        
        # Filename: {time_str}_{clean_rule}_{event_id}.jpg
        filename = f"{time_str}_{clean_rule}_{event.event_id}.jpg"
        
        return dir_path / filename

    def get_snapshot_path(self, event: NormalizedEvent) -> Optional[str]:
        """Returns the absolute path to a snapshot if it exists, otherwise None."""
        path = self._build_path(event)
        return str(path.absolute()) if path.exists() else None

    def snapshot_exists(self, event: NormalizedEvent) -> bool:
        """Checks if a snapshot has already been saved for this event."""
        return self._build_path(event).exists()

    def save_snapshot(self, frame: np.ndarray, event: NormalizedEvent) -> Optional[str]:
        """
        Saves the OpenCV frame to disk if the event is an ALERT_SENT.
        Returns the saved file path, or None if skipped/failed.
        """
        # Only save event/alert snapshots
        if event.status != "ALERT_SENT":
            return None
            
        # Handle invalid frames safely
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            print(f"[SnapshotManager] Invalid frame for event {event.event_id}")
            return None

        file_path = self._build_path(event)
        
        # Avoid duplicate saves for the exact same event
        if file_path.exists():
            return str(file_path.absolute())

        # Create directories automatically
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save the image
            cv2.imwrite(str(file_path), frame)
            return str(file_path.absolute())
        except Exception as e:
            print(f"[SnapshotManager] Failed to save snapshot: {e}")
            return None

    def cleanup_old_snapshots(self, days_to_keep: int = 30) -> int:
        """
        Removes snapshots older than `days_to_keep` days.
        Returns the number of deleted files.
        """
        now = datetime.now()
        deleted_count = 0
        
        # Iterate over all .jpg files in the snapshot directory
        for file_path in self.base_dir.rglob("*.jpg"):
            if file_path.is_file():
                # Parse modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if (now - mtime).days >= days_to_keep:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        print(f"[SnapshotManager] Failed to delete {file_path}: {e}")
                        
        # Clean up empty directories left behind
        for dir_path in sorted(self.base_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                except Exception:
                    pass
                    
        return deleted_count


def run_test():
    print("=" * 60)
    print("AURA SURVEILLANCE - SNAPSHOT MANAGER TEST")
    print("=" * 60)
    
    # Use a separate test directory to avoid polluting real data
    test_dir = "storage/snapshots_test"
    manager = SnapshotManager(base_dir=test_dir)
    
    # 1. Create a synthetic OpenCV frame
    print("\n--- 1. Creating Synthetic Frame ---")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Paint it dark blue
    dummy_frame[:] = (50, 50, 150)
    # Add test text
    cv2.putText(dummy_frame, 'TEST ALERT SNAPSHOT', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    print("Synthetic frame shape:", dummy_frame.shape)
    
    # 2. Create a sample NormalizedEvent
    print("\n--- 2. Creating NormalizedEvent ---")
    event = NormalizedEvent(
        event_id=str(uuid.uuid4()),
        camera_id=1,
        rule_id=5,
        rule_name="Crowd Congestion",
        severity="WARNING",
        status="ALERT_SENT",
        timestamp=datetime.now(),
        details="15 people detected in main lobby",
    )
    print("Event ID:", event.event_id)
    print("Status:", event.status)
    
    # 3. Save the snapshot
    print("\n--- 3. Testing Save Snapshot ---")
    saved_path = manager.save_snapshot(dummy_frame, event)
    print(f"Saved Path: {saved_path}")
    
    # 4. Verify file exists
    print("\n--- 4. Testing Retrieval ---")
    exists = manager.snapshot_exists(event)
    print(f"File exists check: {exists}")
    retrieved_path = manager.get_snapshot_path(event)
    print(f"Retrieved Path: {retrieved_path}")
    
    # 5. Test duplicate handling
    print("\n--- 5. Testing Duplicate Handling ---")
    duplicate_path = manager.save_snapshot(dummy_frame, event)
    print(f"Duplicate Save Path: {duplicate_path}")
    print(f"Duplicate matches original: {duplicate_path == saved_path}")
    
    # 6. Test invalid frame
    print("\n--- 6. Testing Invalid Frame ---")
    invalid_path = manager.save_snapshot(None, event)
    print(f"Invalid frame result: {invalid_path}")
    
    # 7. Test non-ALERT_SENT status
    print("\n--- 7. Testing Non-Alert Status ---")
    event.status = "RESOLVED"
    non_alert_path = manager.save_snapshot(dummy_frame, event)
    print(f"Non-Alert save result: {non_alert_path}")
    
    # 8. Test Cleanup function
    print("\n--- 8. Testing Cleanup ---")
    # Manually change modification time of the test file to be 35 days old
    old_time = time.time() - (35 * 24 * 3600)
    if saved_path and os.path.exists(saved_path):
        os.utime(saved_path, (old_time, old_time))
        
    deleted_count = manager.cleanup_old_snapshots(days_to_keep=30)
    print(f"Cleanup deleted {deleted_count} old snapshots (should be 1).")
    
    # Verify it's gone
    event.status = "ALERT_SENT" # Reset status for lookup check
    print(f"File exists after cleanup: {manager.snapshot_exists(event)}")
    
    # Clean up test directory (delete everything)
    manager.cleanup_old_snapshots(days_to_keep=-1)

    print("\n" + "=" * 60)
    print("SNAPSHOT MANAGER TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
