import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.app.sandbox_manager import sandbox_manager

router = APIRouter(
    prefix="/api/sandbox",
    tags=["Sandbox"],
)

UPLOAD_DIR = Path("storage/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov')):
        raise HTTPException(status_code=400, detail="Unsupported video format.")
        
    job_id = sandbox_manager.create_job()
    
    file_path = UPLOAD_DIR / f"sandbox_{job_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    sandbox_manager.start_job(job_id, str(file_path))
    
    return {"job_id": job_id, "status": "UPLOADING"}

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = sandbox_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return job

@router.get("/video/{filename}")
async def get_processed_video(filename: str):
    from fastapi.responses import FileResponse
    file_path = Path("storage/processed") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    media_type = "video/webm" if filename.endswith(".webm") else "video/mp4"
    return FileResponse(file_path, media_type=media_type)
