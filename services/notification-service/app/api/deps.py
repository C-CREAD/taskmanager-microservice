from typing import Annotated
from dataclasses import dataclass

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


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if not user_id or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        username=payload.get("username", ""),
    )


# Type aliases
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
