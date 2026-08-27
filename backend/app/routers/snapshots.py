from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

SNAPSHOTS_DIR = Path("storage/snapshots").resolve()

router = APIRouter(
    prefix="/api/snapshots",
    tags=["Snapshots"],
)

@router.get("/{filepath:path}")
def get_snapshot(filepath: str):
    # Security: Prevent path traversal
    if ".." in filepath or filepath.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    requested_path = (SNAPSHOTS_DIR / filepath).resolve()
    
    if not str(requested_path).startswith(str(SNAPSHOTS_DIR)):
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    if not requested_path.exists() or not requested_path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot not found")
        
    return FileResponse(str(requested_path))
