"""User management endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError

from backend.models.user import User
from backend.services.db.postgres_connector import database_service

router = APIRouter()


class UserRegistrationRequest(BaseModel):
    """User registration request model."""
    email: EmailStr
    password: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""
    id: int
    email: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/register", tags=["Users"], response_model=UserResponse)
async def register_user(user_data: UserRegistrationRequest) -> UserResponse:
    """Register a new user.
    
    Args:
    - `user_data`: User registration data (email required, password optional)
        
    Returns:
    - `UserResponse`: Created user information
        
    Raises:
    - `HTTPException`: If email already exists or registration fails
    """
    try:
        # Hash password if provided, otherwise use empty string
        # Note: In production, you might want to handle this differently
        if user_data.password:
            hashed_password = User.hash_password(user_data.password)
        else:
            # Use a default empty hash if no password provided
            hashed_password = User.hash_password("")
        
        # Create user
        user = await database_service.create_user(
            email=user_data.email,
            password=hashed_password
        )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
        
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/{user_id}", tags=["Users"], response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    """Get user by ID.
    
    Args:
    - `user_id`: User ID
        
    Returns:
    - `UserResponse`: User information
        
    Raises:
    - `HTTPException`: If user not found
    """
    user = await database_service.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at.isoformat() if user.created_at else None
    )


@router.get("/email/{email}", tags=["Users"], response_model=UserResponse)
async def get_user_by_email(email: str) -> UserResponse:
    """Get user by email.
    
    Args:
    - `email`: User email address
        
    Returns:
    - `UserResponse`: User information
        
    Raises:
    - `HTTPException`: If user not found
    """
    user = await database_service.get_user_by_email(email)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at.isoformat() if user.created_at else None
    )
