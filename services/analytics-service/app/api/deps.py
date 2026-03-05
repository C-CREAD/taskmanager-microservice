from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import decode_token
from app.db.session import get_db

bearer_scheme = HTTPBearer()


@dataclass
class CurrentUser:
    id: str
    email: str
    username: str
    raw_token: str  # passed through to downstream service calls


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> CurrentUser:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access" or not payload.get("sub"):
            raise exc
    except JWTError:
        raise exc

    return CurrentUser(
        id=payload["sub"],
        email=payload.get("email", ""),
        username=payload.get("username", ""),
        raw_token=credentials.credentials,
    )


AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
