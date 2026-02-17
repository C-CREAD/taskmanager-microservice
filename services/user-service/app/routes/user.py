# app/routes/user.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_database
from app.schemas import (
    UserCreate, UserUpdate, UserResponse, UserPasswordReset,
)
from app.services import UserService, AuthService
from app.models import User
from app.core.security import decode_token
from typing import List

router = APIRouter(prefix="/api/users", tags=["users"])
security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: AsyncSession = Depends(get_database),
) -> User:
    """Get current user from Bearer token"""

    # Decode token
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Get user from database
    user_id = payload.get("sub")
    user = await UserService.get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_database)):
    """Register new user"""
    existing_user = await UserService.get_user_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_user = await UserService.get_user_by_username(session, user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = await UserService.create_user(session, user_data)
    return UserResponse.from_orm(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
        user_data: UserUpdate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_database),
):
    """Update current user profile"""
    updated_user = await UserService.update_user(session, current_user, user_data)
    return UserResponse.from_orm(updated_user)


@router.post("/change-password")
async def change_password(
        password_data: UserPasswordReset,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_database),
):
    """Change user password"""
    success = await AuthService.change_password(
        session, current_user,
        password_data.old_password,
        password_data.new_password,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Invalid old password")

    return {"message": "Password changed successfully"}


@router.get("", response_model=List[UserResponse])
async def get_all_users(skip: int = 0, limit: int = 100, session: AsyncSession = Depends(get_database)):
    """Get all users"""
    users = await UserService.get_all_users(session, skip, limit)
    return [UserResponse.from_orm(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, session: AsyncSession = Depends(get_database)):
    """Get user by ID"""
    user = await UserService.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)


@router.delete("/me")
async def delete_current_user(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_database),
):
    """Delete current user (soft delete)"""
    await UserService.delete_user(session, current_user)
    return {"message": "User deleted successfully"}