from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.log_service import LogService
from app.middleware.auth_middleware import get_current_user
import os

router = APIRouter()
log_service = LogService()

@router.get("/download/{video_id}")
async def download_log(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download log file (zip) của video đã xử lý
    """
    user_id = int(current_user.get("sub"))
    
    # Lấy đường dẫn file log
    log_file_path = log_service.get_log_file_path(db, video_id, user_id)
    
    # Lấy tên file để đặt tên khi download từ đường dẫn log_file_path
    filename = os.path.basename(log_file_path)
    
    # Trả về file để download
    return FileResponse(
        path=log_file_path,
        filename=filename,
        media_type='application/zip',
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/info/{video_id}")
async def get_log_info(
    video_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin log của video
    """
    user_id = int(current_user.get("sub"))
    video = log_service.get_video_info(db, video_id, user_id)
    
    return {
        "video_id": video.id,
        "filename": video.filename,
        "status": video.status,
        "log_path": video.log_path,
        "has_log": video.log_path is not None and os.path.exists(video.log_path) if video.log_path else False
    }

