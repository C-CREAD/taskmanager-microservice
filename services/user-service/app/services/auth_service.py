from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.services.user_service import UserService
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas import TokenResponse, UserResponse
from typing import Optional
from datetime import datetime


class AuthService:
    """Authentication service representing the processes of performing:
     - user logins
     - user password changes
     - token refreshing

     """

    @staticmethod
    async def authenticate_user(
            session: AsyncSession,
            username: str,
            password: str
    ) -> Optional[User]:
        """Authenticate user with username and password"""
        user = await UserService.get_user_by_username(session, username)

        if not user or not verify_password(password, user.password):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        user.login_count += 1
        await session.commit()
        await session.refresh(user)

        return user

    @staticmethod
    async def login(
            session: AsyncSession,
            username: str,
            password: str
    ) -> Optional[TokenResponse]:
        """Performs user login and return tokens"""
        user = await AuthService.authenticate_user(session, username, password)

        if not user:
            return None

        # Create tokens
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.from_orm(user),
        )

    @staticmethod
    async def refresh_access_token(
            session: AsyncSession,
            refresh_token: str
    ) -> Optional[str]:
        """Get new access token using refresh token"""
        payload = decode_token(refresh_token)

        if not payload:
            return None

        user_id = payload.get("sub")
        user = await UserService.get_user_by_id(session, user_id)

        if not user or not user.is_active:
            return None

        new_access_token = create_access_token({"sub": user.id})
        return new_access_token

    @staticmethod
    async def change_password(
            session: AsyncSession,
            user: User,
            old_password: str,
            new_password: str
    ) -> bool:
        """Change user password"""
        if not verify_password(old_password, user.password):
            return False

        user.password = hash_password(new_password)
        await session.commit()
        return True