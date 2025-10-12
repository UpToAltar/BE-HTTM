from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import AuthService
from app.schemas.schemas import UserCreate, UserResponse, LoginRequest, LoginResponse
from app.middleware.auth_middleware import get_current_user

router = APIRouter()
auth_service = AuthService()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        return auth_service.create_user(db, user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=LoginResponse)
def login_user(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login user"""
    user = auth_service.authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create access token
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return LoginResponse(
        user=user,
        access_token=access_token,
        token_type="bearer",
        message="Login successful"
    )

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information from JWT token"""
    return {
        "user_id": current_user.get("sub"),
        "username": current_user.get("username"),
        "exp": current_user.get("exp")
    }
