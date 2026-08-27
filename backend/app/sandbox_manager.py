import uuid
import threading
from typing import Dict, Any, Optional
from pathlib import Path

from backend.app.video_processor import process_video
from backend.app.sandbox_pipeline import SandboxPipeline

class SandboxJobManager:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        
    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "IDLE",
            "progress": 0.0,
            "processed_frames": 0,
            "total_frames": 0,
            "detections": 0,
            "events_generated": 0,
            "output_video": None,
            "error": None
        }
        return job_id
        
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)
        
    def start_job(self, job_id: str, input_video_path: str):
        if job_id not in self.jobs:
            return
            
        self.jobs[job_id]["status"] = "CONFIGURING_RULES"
        
        # Start background thread
        thread = threading.Thread(target=self._run_job_sync, args=(job_id, input_video_path))
        thread.daemon = True
        thread.start()
        
    def _run_job_sync(self, job_id: str, input_video_path: str):
        job = self.jobs[job_id]
        
        try:
            job["status"] = "INITIALIZING_AI"
            
            # Using a mock camera ID for the sandbox
            camera_id = 999
            pipeline = SandboxPipeline(camera_id=camera_id)
            
            job["status"] = "PROCESSING"
            
            def on_init(width: int, height: int, fps: float):
                pipeline.initialize(width, height, fps)
                
            def on_frame(frame, timestamp, detections_data):
                pipeline.process_frame(frame, timestamp, detections_data)
                
            def on_progress(processed, total, detections):
                job["processed_frames"] = processed
                job["total_frames"] = total
                job["detections"] = detections
                job["events_generated"] = pipeline.total_events_generated
                if total > 0:
                    job["progress"] = min(100.0, (processed / total) * 100)
            
            output_filename = f"sandbox_{job_id}.webm"
            
            output_path = process_video(
                video_path=input_video_path,
                output_filename=output_filename,
                init_callback=on_init,
                frame_callback=on_frame,
                progress_callback=on_progress
            )
            
            job["output_video"] = f"/api/sandbox/video/{output_filename}"
            job["status"] = "AI_PLAYBACK_ACTIVE"
            job["progress"] = 100.0
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            job["status"] = "FAILED"
            job["error"] = str(e)


# Global instance
sandbox_manager = SandboxJobManager()

def run_test():
    import time
    print("=" * 60)
    print("AURA SURVEILLANCE - SANDBOX MANAGER TEST")
    print("=" * 60)
    
    BASE_DIR = Path(__file__).resolve().parents[2]
    VIDEO_PATH = BASE_DIR / "storage" / "videos" / "sample.mp4"
    
    if not VIDEO_PATH.exists():
        print(f"Test video not found: {VIDEO_PATH}")
        return
        
    job_id = sandbox_manager.create_job()
    print(f"Created job: {job_id}")
    
    sandbox_manager.start_job(job_id, str(VIDEO_PATH))
    
    while True:
        job = sandbox_manager.get_job(job_id)
        print(f"[{job['status']}] Progress: {job['progress']:.1f}% | Frames: {job['processed_frames']}/{job['total_frames']} | Evts: {job['events_generated']}")
        
        if job["status"] in ["AI_PLAYBACK_ACTIVE", "COMPLETED", "FAILED"]:
            break
            
        time.sleep(2)
        
    print("Test finished.")
    print("Final Job State:", job)

if __name__ == "__main__":
    run_test()
