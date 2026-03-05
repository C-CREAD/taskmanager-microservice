from jose import JWTError, jwt
from app.core.config import settings


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def get_user_id_from_token(token: str) -> str:
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id or payload.get("type") != "access":
        raise JWTError("Invalid token claims.")
    return user_id
