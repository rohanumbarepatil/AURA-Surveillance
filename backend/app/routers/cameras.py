from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Camera
from ..schemas import CameraCreate, CameraResponse, CameraUpdate, EventResponse
from ..event_repository import EventRepository

repo = EventRepository()

router = APIRouter(
    prefix="/api/cameras",
    tags=["Cameras"],
)


@router.post("/", response_model=CameraResponse, status_code=201)
def create_camera(
    camera_data: CameraCreate,
    db: Session = Depends(get_db),
):
    camera = Camera(
        name=camera_data.name,
        source=camera_data.source,
        source_type=camera_data.source_type,
        status="DISCONNECTED",
        enabled=True,
    )

    db.add(camera)
    db.commit()
    db.refresh(camera)

    return camera


@router.get("/", response_model=list[CameraResponse])
def list_cameras(
    db: Session = Depends(get_db),
):
    return db.query(Camera).order_by(Camera.id).all()


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db),
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail="Camera not found",
        )

    return camera


@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: int,
    camera_data: CameraUpdate,
    db: Session = Depends(get_db),
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail="Camera not found",
        )

    update_data = camera_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(camera, field, value)

    db.commit()
    db.refresh(camera)

    return camera


@router.delete("/{camera_id}")
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()

    if camera is None:
        raise HTTPException(
            status_code=404,
            detail="Camera not found",
        )

    db.delete(camera)
    db.commit()

    return {
        "message": "Camera deleted successfully",
        "camera_id": camera_id,
    }


@router.get("/{camera_id}/events", response_model=list[EventResponse])
def get_camera_events(
    camera_id: int,
    limit: int = 100,
):
    return repo.get_events_by_camera(camera_id, limit=limit)