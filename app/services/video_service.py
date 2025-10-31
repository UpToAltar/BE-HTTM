from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.models import Video
from app.schemas.schemas import VideoResponse, PlateDetectionResult
from fastapi import UploadFile, HTTPException, status
import os
import uuid
from datetime import datetime
from app.services.plate_service import PlateService
from app.services.traffic_light_service import TrafficLightService
import cv2
import csv
import shutil
import zipfile

class VideoService:
    def __init__(self):
        self.video_upload_dir = "app/upload/videos"
        self.image_upload_dir = "app/upload/images"
        self.logs_dir = "app/upload/logs"
        self.max_file_size = 100 * 1024 * 1024
        self.allowed_video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}
        self.allowed_image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        
        os.makedirs(self.video_upload_dir, exist_ok=True)
        os.makedirs(self.image_upload_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
    
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
    
    def handle_logic_video(self, db: Session, video_record: VideoResponse, file: UploadFile) -> List[PlateDetectionResult]:
        plate_service = PlateService()
        traffic_light_service = TrafficLightService()
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        file_path = video_record.filepath
        
        detected_plates = []
        is_red_light_detected = False  # Biến theo dõi trạng thái đèn đỏ
        
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
                    # Detect đèn đỏ trong frame
                    has_red_light = traffic_light_service.detect_red_light(frame)
                    if has_red_light:
                        is_red_light_detected = True
                    
                    timestamp = frame_count / fps
                    plates = plate_service.detect_and_recognize(frame, timestamp=timestamp, frame_number=frame_number)
                    detected_plates.extend(plates)
                    frame_number += 1
                
                frame_count += 1
            
            cap.release()
        else:
            image = cv2.imread(file_path)
            # Detect đèn đỏ trong ảnh
            has_red_light = traffic_light_service.detect_red_light(image)
            if has_red_light:
                is_red_light_detected = True
            
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

        # Tạo log folder và file CSV
        if plate_results:
            log_zip_path = self._create_log_package(video_record, plate_results, db)
        
        return plate_results
    
    def _create_log_package(self, video_record: VideoResponse, plate_results: List[PlateDetectionResult], db: Session) -> str:
        """
        Tạo package log bao gồm CSV và folder crops, sau đó zip lại
        """
        # Tạo tên folder duy nhất
        log_folder_name = f"log_{video_record.id}_{uuid.uuid4().hex[:8]}"
        log_folder_path = os.path.join(self.logs_dir, log_folder_name)
        
        # Tạo thư mục log
        os.makedirs(log_folder_path, exist_ok=True)
        
        # Tạo thư mục crops trong log folder
        crops_folder_path = os.path.join(log_folder_path, "crops")
        os.makedirs(crops_folder_path, exist_ok=True)
        
        # Tạo file CSV
        csv_file_path = os.path.join(log_folder_path, "detection_results.csv")
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['plate_number', 'confidence', 'bbox', 'timestamp', 'frame_number', 'crop_filename']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for plate in plate_results:
                # Copy file crop vào folder crops
                if os.path.exists(plate.crop_path):
                    crop_filename = os.path.basename(plate.crop_path)
                    new_crop_path = os.path.join(crops_folder_path, crop_filename)
                    shutil.copy2(plate.crop_path, new_crop_path)
                else:
                    crop_filename = "not_found"
                
                # Ghi vào CSV
                writer.writerow({
                    'plate_number': plate.plate_number,
                    'confidence': f"{plate.confidence:.4f}",
                    'bbox': f"[{','.join(map(str, plate.bbox))}]",
                    'timestamp': plate.timestamp if plate.timestamp is not None else '',
                    'frame_number': plate.frame_number if plate.frame_number is not None else '',
                    'crop_filename': crop_filename
                })
        
        # Zip folder
        zip_file_path = os.path.join(self.logs_dir, f"{log_folder_name}.zip")
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(log_folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, log_folder_path)
                    zipf.write(file_path, arcname)
        
        # Xóa folder tạm sau khi zip
        shutil.rmtree(log_folder_path)
        
        # Chuẩn hóa đường dẫn
        normalized_zip_path = zip_file_path.replace("\\", "/")
        
        # Cập nhật log_path vào database
        video_db = db.query(Video).filter(Video.id == video_record.id).first()
        if video_db:
            video_db.log_path = normalized_zip_path
            video_db.status = "completed"
            db.commit()
        
        return normalized_zip_path
    