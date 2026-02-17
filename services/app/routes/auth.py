from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_database
from app.schemas import LoginRequest, RefreshTokenRequest, TokenResponse
from app.services import AuthService

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
        login_data: LoginRequest,
        session: AsyncSession = Depends(get_database)
):
    """Login user with username and password"""
    result = await AuthService.login(
        session,
        login_data.username,
        login_data.password
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return result


@router.post("/refresh")
async def refresh_token(
        request: RefreshTokenRequest,
        session: AsyncSession = Depends(get_database)
):
    """Refresh access token"""
    new_token = await AuthService.refresh_access_token(
        session,
        request.refresh_token
    )

    if not new_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    return {"access_token": new_token, "token_type": "bearer"}