from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.models import Video
from app.schemas.schemas import VideoResponse, PlateDetectionResult
from fastapi import UploadFile, HTTPException, status
import os
import uuid
from datetime import datetime
from app.services.plate_service import PlateService
import cv2

class VideoService:
    def __init__(self):
        self.video_upload_dir = "app/upload/videos"
        self.image_upload_dir = "app/upload/images"
        self.max_file_size = 100 * 1024 * 1024
        self.allowed_video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}
        self.allowed_image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        
        os.makedirs(self.video_upload_dir, exist_ok=True)
        os.makedirs(self.image_upload_dir, exist_ok=True)
    
    def get_video_history_service(self, db: Session, user_id: int) -> List[VideoResponse]:
        videos = db.query(Video).filter(Video.user_id == user_id).all()
        return [VideoResponse.from_orm(video) for video in videos]
    
    async def upload_file_service(self, db: Session, user_id: int, file: UploadFile) -> VideoResponse:
        # Kiểm tra kiểu file
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Kiểm tra định dạng file
        if file_extension not in self.allowed_video_extensions and file_extension not in self.allowed_image_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: videos ({', '.join(self.allowed_video_extensions)}) and images ({', '.join(self.allowed_image_extensions)})"
            )
        
        # Kiểm tra kích thước file
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {self.max_file_size / (1024 * 1024)}MB"
            )
        
        # Xác định thư mục upload
        if file_extension in self.allowed_video_extensions:
            upload_dir = self.video_upload_dir
        else:
            upload_dir = self.image_upload_dir
        
        # Tạo tên file duy nhất
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Lưu file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Chuẩn hóa đường dẫn
        normalized_path = file_path.replace("\\", "/")
        
        # Tạo record trong database
        video_record = Video(
            user_id=user_id,
            filename=file.filename,
            filepath=normalized_path,
            status="processing",
            created_at=datetime.utcnow()
        )
        
        db.add(video_record)
        db.commit()
        db.refresh(video_record)
        
        return VideoResponse.from_orm(video_record)
    
    def handle_logic_video(self, video_record: VideoResponse, file: UploadFile) -> List[PlateDetectionResult]:
        plate_service = PlateService()
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        file_path = video_record.filepath
        
        detected_plates = []
        
        if file_extension in self.allowed_video_extensions:
            cap = cv2.VideoCapture(file_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * 2)
            
            frame_count = 0
            frame_number = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / fps
                    plates = plate_service.detect_and_recognize(frame, timestamp=timestamp, frame_number=frame_number)
                    detected_plates.extend(plates)
                    frame_number += 1
                
                frame_count += 1
            
            cap.release()
        else:
            image = cv2.imread(file_path)
            detected_plates = plate_service.detect_and_recognize(image)
        
        unique_plates = plate_service.get_unique_plates(detected_plates)
        
        plate_results = [
            PlateDetectionResult(
                plate_number=plate["plate_number"],
                confidence=plate["confidence"],
                crop_path=plate["crop_path"],
                bbox=plate["bbox"],
                timestamp=plate.get("timestamp"),
                frame_number=plate.get("frame_number")
            )
            for plate in unique_plates
        ]


        
        return plate_results
    