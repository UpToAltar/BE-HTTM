from pydantic import BaseModel
from datetime import datetime
from typing import Optional

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
