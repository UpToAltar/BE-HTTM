from sqlalchemy.orm import Session
from typing import Optional
from app.models.models import User
from app.schemas.schemas import UserCreate, UserResponse
import hashlib
import secrets
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(plain_password) == hashed_password
    
    def create_user(self, db: Session, user: UserCreate) -> UserResponse:
        """Create a new user"""
        # Check if username already exists
        existing_user = self.get_user_by_username(db, user.username)
        if existing_user:
            raise ValueError("Username already exists")
        
        hashed_password = self.hash_password(user.password)
        db_user = User(
            username=user.username,
            password_hash=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return UserResponse.from_orm(db_user)
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[UserResponse]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(db, username)
        if not user:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        return UserResponse.from_orm(user)
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[UserResponse]:
        """Get user by ID"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return UserResponse.from_orm(user)
        return None
    
    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
