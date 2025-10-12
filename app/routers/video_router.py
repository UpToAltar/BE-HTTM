from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services.video_service import VideoService
from app.services.auth_service import AuthService
from app.schemas.schemas import VideoResponse, UserResponse
from app.middleware.auth_middleware import get_current_user

router = APIRouter()
video_service = VideoService()
auth_service = AuthService()

@router.get("/", response_model=List[VideoResponse])
def get_my_videos(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all videos for the current authenticated user"""
    user_id = int(current_user.get("sub"))
    return video_service.get_videos_by_user(db, user_id)

@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    """Get video by ID"""
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    return video

@router.get("/", response_model=List[VideoResponse])
def get_all_videos(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all videos (requires authentication)"""
    return video_service.get_all_videos(db)
