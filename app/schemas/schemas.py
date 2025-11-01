from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    message: str

class VideoBase(BaseModel):
    filename: str
    filepath: str
    status: Optional[str] = "processing"

class VideoResponse(VideoBase):
    id: int
    log_path: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class ViolationBase(BaseModel):
    plate_number: str
    timestamp_frame: str
    snapshot_path: str

class ViolationResponse(ViolationBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class PlateDetectionResult(BaseModel):
    plate_number: str
    confidence: float
    crop_path: str
    bbox: list
    timestamp: Optional[float] = None
    frame_number: Optional[int] = None

class VideoUploadResponse(BaseModel):
    video: VideoResponse
    detected_plates: List[PlateDetectionResult]