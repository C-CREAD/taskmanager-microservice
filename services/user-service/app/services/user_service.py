from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse
from app.core.security import hash_password
from typing import Optional


class UserService:
    """User service business logic"""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        user_data: UserCreate
    ) -> User:
        """Create a new user"""
        user = User(
            email=user_data.email,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password=hash_password(user_data.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def get_user_by_email(
        session: AsyncSession,
        email: str
    ) -> Optional[User]:
        """Get user by email"""
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(
        session: AsyncSession,
        username: str
    ) -> Optional[User]:
        """Get user by username"""
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(
        session: AsyncSession,
        user_id: str
    ) -> Optional[User]:
        """Get user by ID"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_users(session: AsyncSession, skip: int = 0, limit: int = 100):
        """Get all users with pagination"""
        result = await session.execute(
            select(User).offset(skip).limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def update_user(
        session: AsyncSession,
        user: User,
        user_data: UserUpdate
    ) -> User:
        """Update user details"""
        if user_data.email:
            user.email = user_data.email
        if user_data.first_name:
            user.first_name = user_data.first_name
        if user_data.last_name:
            user.last_name = user_data.last_name

        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def delete_user(
        session: AsyncSession,
        user: User
    ) -> bool:
        """Soft delete user (deactivate)"""
        user.is_active = False
        await session.commit()
        return True

    @staticmethod
    async def verify_user(
        session: AsyncSession,
        user: User
    ) -> User:
        """Mark user as verified"""
        user.is_verified = True
        await session.commit()
        await session.refresh(user)
        return user