from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services.video_service import VideoService
from app.services.auth_service import AuthService
from app.schemas.schemas import VideoResponse, UserResponse, VideoUploadResponse, PlateDetectionResult
from app.middleware.auth_middleware import get_current_user

router = APIRouter()
video_service = VideoService()
auth_service = AuthService()

@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = int(current_user.get("sub"))
    video_record : VideoResponse = await video_service.upload_file_service(db, user_id, file)
    
    detected_plates : List[PlateDetectionResult] = video_service.handle_logic_video(video_record, file)
    
    return VideoUploadResponse(
        video=video_record,
        detected_plates=detected_plates
    )

@router.get("/", response_model=List[VideoResponse])
def get_video_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = int(current_user.get("sub"))
    return video_service.get_video_history_service(db, user_id)

