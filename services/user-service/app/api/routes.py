from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, CurrentSuperuser, DB
from app.core.config import settings
from app.core.jwt import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import (
    AccessTokenResponse,
    ChangePasswordRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserInternalResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter()


# ── Auth endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(payload: UserRegisterRequest, db: DB):
    # Check for duplicate email / username
    existing = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists.",
        )

    await db.refresh(user)
    return user


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Login and receive JWT tokens",
)
async def login(payload: UserLoginRequest, db: DB):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "username": user.username},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/auth/refresh",
    response_model=AccessTokenResponse,
    summary="Use a refresh token to get a new access token",
)
async def refresh_token(payload: RefreshTokenRequest, db: DB):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )
    try:
        token_data = decode_token(payload.refresh_token)
        if token_data.get("type") != "refresh":
            raise credentials_exception
        user_id = token_data.get("sub")
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    new_access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "username": user.username},
    )

    return AccessTokenResponse(
        access_token=new_access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout (blacklist the current access token)",
)
async def logout(request: Request, _: CurrentUser):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    blacklist_token(token)


# ── User profile endpoints ────────────────────────────────────────────────────────

@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user's profile",
)
async def get_me(current_user: CurrentUser):
    return current_user


@router.patch(
    "/users/me",
    response_model=UserResponse,
    summary="Update the currently authenticated user's profile",
)
async def update_me(payload: UserUpdateRequest, current_user: CurrentUser, db: DB):
    update_data = payload.model_dump(exclude_unset=True)

    if "username" in update_data:
        existing = await db.execute(
            select(User).where(
                User.username == update_data["username"],
                User.id != current_user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken.",
            )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post(
    "/users/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the authenticated user's password",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DB,
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    await db.flush()


@router.delete(
    "/users/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate (soft-delete) the authenticated user's account",
)
async def deactivate_me(current_user: CurrentUser, db: DB):
    current_user.is_active = False
    current_user.updated_at = datetime.now(timezone.utc)
    await db.flush()


# ── Internal / service-to-service endpoint ─────────────────────────────────────────

@router.get(
    "/internal/users/{user_id}",
    response_model=UserInternalResponse,
    summary="[Internal] Fetch minimal user info for other microservices",
    include_in_schema=False,  # Hidden from public Swagger docs
)
async def get_user_internal(user_id: str, db: DB):
    """
    Called by Task Service, Notification Service, etc. to verify a user exists.
    This endpoint should be protected at the Nginx level (not publicly accessible).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


# ── Admin endpoints ───────────────────────────────────────────────────────────────

@router.get(
    "/admin/users",
    response_model=list[UserResponse],
    summary="[Admin] List all users",
)
async def list_users(
    _: CurrentSuperuser,
    db: DB,
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


@router.patch(
    "/admin/users/{user_id}/activate",
    response_model=UserResponse,
    summary="[Admin] Activate or deactivate a user account",
)
async def toggle_user_active(
    user_id: str,
    is_active: bool,
    _: CurrentSuperuser,
    db: DB,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = is_active
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(user)
    return user
