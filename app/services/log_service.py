from sqlalchemy.orm import Session
from typing import Optional
from app.models.models import Video
from fastapi import HTTPException, status
import os

class LogService:
    def __init__(self):
        self.logs_dir = "app/upload/logs"
    
    def get_log_file_path(self, db: Session, video_id: int, user_id: int) -> str:
        """
        Lấy đường dẫn file log của video
        """
        # Kiểm tra video có tồn tại và thuộc về user không
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video không tồn tại hoặc bạn không có quyền truy cập"
            )
        
        # Kiểm tra video đã được xử lý chưa
        if video.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video đang trong trạng thái '{video.status}'. Chỉ có thể tải log của video đã hoàn thành."
            )
        
        # Kiểm tra log_path có tồn tại không
        if not video.log_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File log chưa được tạo cho video này"
            )
        
        # Kiểm tra file có tồn tại trên hệ thống không, 
        if not os.path.exists(video.log_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File log không tồn tại trên hệ thống"
            )
        
        return video.log_path
            

    def get_video_info(self, db: Session, video_id: int, user_id: int) -> Video:
        """
        Lấy thông tin video
        """
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video không tồn tại hoặc bạn không có quyền truy cập"
            )
        
        return video

