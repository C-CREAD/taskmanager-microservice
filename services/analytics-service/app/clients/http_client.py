"""
Async HTTP client for inter-service REST calls.
All communication to Task Service and User Service lives here,
keeping aggregators clean and easily mockable in tests.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Shared async client (connection pooling)
_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def close_http_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()


class TaskServiceClient:
    """Thin wrapper around Task Service REST endpoints."""

    BASE = settings.TASK_SERVICE_URL

    @staticmethod
    async def get_user_stats(user_id: str, auth_token: str) -> dict:
        """
        GET /api/tasks/stats/
        Returns: {total, by_status, by_priority, overdue, due_today, completed_today}
        """
        client = await get_http_client()
        resp = await client.get(
            f"{TaskServiceClient.BASE}/api/tasks/stats/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    async def get_tasks_page(
        user_id: str,
        auth_token: str,
        page: int = 1,
        page_size: int = 100,
        status: str | None = None,
    ) -> dict:
        """Paginated task list — used for deep aggregation (trend computation)."""
        client = await get_http_client()
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        resp = await client.get(
            f"{TaskServiceClient.BASE}/api/tasks/",
            params=params,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    async def get_all_completed_tasks(user_id: str, auth_token: str) -> list[dict]:
        """
        Fetch all DONE tasks for a user (paginates automatically).
        Used for trend and on-time rate calculations.
        """
        all_tasks: list[dict] = []
        page = 1
        while True:
            data = await TaskServiceClient.get_tasks_page(
                user_id, auth_token, page=page, page_size=100, status="done"
            )
            all_tasks.extend(data.get("results", []))
            if not data.get("next"):
                break
            page += 1
            if page > 20:  # safety cap — never fetch more than 2000 tasks
                break
        return all_tasks


class UserServiceClient:
    """Thin wrapper around User Service internal endpoints."""

    BASE = settings.USER_SERVICE_URL

    @staticmethod
    async def get_user(user_id: str, auth_token: str) -> dict:
        client = await get_http_client()
        resp = await client.get(
            f"{UserServiceClient.BASE}/api/internal/users/{user_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        resp.raise_for_status()
        return resp.json()
