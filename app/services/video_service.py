from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.models import Video
from app.schemas.schemas import VideoResponse

class VideoService:
    def __init__(self):
        pass
    
    def get_videos_by_user(self, db: Session, user_id: int) -> List[VideoResponse]:
        """Get all videos for a specific user"""
        videos = db.query(Video).filter(Video.user_id == user_id).all()
        return [VideoResponse.from_orm(video) for video in videos]
    
    def get_video_by_id(self, db: Session, video_id: int) -> Optional[VideoResponse]:
        """Get video by ID"""
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            return VideoResponse.from_orm(video)
        return None
    
    def get_all_videos(self, db: Session) -> List[VideoResponse]:
        """Get all videos"""
        videos = db.query(Video).all()
        return [VideoResponse.from_orm(video) for video in videos]