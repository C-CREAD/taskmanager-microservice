"""
Custom DRF authentication backend.

Instead of re-implementing JWT verification, this class decodes the token
locally (same secret key) and then optionally verifies the user is still
active by calling the User Service's internal endpoint.

For maximum security, decode AND verify against the User Service on every
request. For performance, decode locally and only call the User Service
on token refresh or when a 404 is returned from the DB.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings
from jose import JWTError, jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

logger = logging.getLogger(__name__)


@dataclass
class RemoteUser:
    """
    Lightweight user object injected into request.user.
    Not a Django model — we store no user data in the Task Service DB.
    """
    id: str
    email: str
    username: str
    is_active: bool = True
    is_authenticated: bool = True
    is_anonymous: bool = False

    def __str__(self) -> str:
        return self.username


class RemoteJWTAuthentication(BaseAuthentication):
    """
    Decode the Bearer JWT locally, then verify the user is still active
    by calling the User Service internal endpoint.
    """

    def authenticate(self, request: Request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None  # Let other backends try, or 401 from permission class

        token = auth_header.removeprefix("Bearer ").strip()

        # Step 1: Decode locally
        try:
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT["SIGNING_KEY"],
                algorithms=[settings.SIMPLE_JWT["ALGORITHM"]],
            )
        except JWTError as exc:
            raise AuthenticationFailed(f"Invalid or expired token: {exc}")

        if payload.get("type") != "access":
            raise AuthenticationFailed("Token type must be 'access'.")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationFailed("Token missing subject claim.")

        # Step 2: Verify user is still active via User Service internal API
        user_data = self._fetch_user(user_id, token)

        user = RemoteUser(
            id=user_data["id"],
            email=user_data["email"],
            username=user_data["username"],
            is_active=user_data["is_active"],
        )

        if not user.is_active:
            raise AuthenticationFailed("User account is inactive.")

        return (user, token)

    def _fetch_user(self, user_id: str, token: str) -> dict:
        """Call User Service internal endpoint to verify the user exists and is active."""
        url = f"{settings.USER_SERVICE_URL}/api/internal/users/{user_id}"
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 404:
                raise AuthenticationFailed("User not found.")
            if resp.status_code != 200:
                logger.warning("User Service returned %s for user %s", resp.status_code, user_id)
                raise AuthenticationFailed("Could not verify user identity.")
            return resp.json()
        except httpx.RequestError as exc:
            logger.error("User Service unreachable: %s", exc)
            raise AuthenticationFailed("Authentication service unavailable.")

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"
