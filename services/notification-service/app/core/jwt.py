from jose import JWTError, jwt
from app.core.config import settings


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def get_user_id_from_token(token: str) -> str:
    """Extract user ID (sub claim) from a valid JWT. Raises JWTError on failure."""
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise JWTError("Token missing subject claim.")
    if payload.get("type") != "access":
        raise JWTError("Token type must be 'access'.")
    return user_id
