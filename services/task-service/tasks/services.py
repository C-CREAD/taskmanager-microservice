"""
Service layer — keeps views thin by isolating business logic here.
All inter-service REST calls live in this module.
"""
from __future__ import annotations

import logging

import httpx
from django.conf import settings
from django.utils import timezone

from .models import Task

logger = logging.getLogger(__name__)


def notify_task_created(task: Task, auth_token: str) -> None:
    """
    Fire-and-forget POST to the Notification Service when a task is created.
    Errors are logged but never propagated — notifications are best-effort.
    """
    payload = {
        "type": "task_created",
        "recipient_id": task.owner_id,
        "task_id": task.id,
        "task_title": task.title,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }
    _post_notification(payload, auth_token)


def notify_task_assigned(task: Task, auth_token: str) -> None:
    """Notify the assignee when a task is assigned to them."""
    if not task.assignee_id:
        return
    payload = {
        "type": "task_assigned",
        "recipient_id": task.assignee_id,
        "task_id": task.id,
        "task_title": task.title,
        "assigned_by": task.owner_id,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }
    _post_notification(payload, auth_token)


def notify_task_completed(task: Task, auth_token: str) -> None:
    """Notify the owner when a task transitions to DONE."""
    payload = {
        "type": "task_completed",
        "recipient_id": task.owner_id,
        "task_id": task.id,
        "task_title": task.title,
    }
    _post_notification(payload, auth_token)


def mark_task_complete(task: Task) -> Task:
    """Set completed_at timestamp and status when a task is done."""
    task.status = Task.Status.DONE
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at", "updated_at"])
    return task


def _post_notification(payload: dict, auth_token: str) -> None:
    url = f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/internal"
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        if resp.status_code >= 400:
            logger.warning(
                "Notification Service returned %s: %s", resp.status_code, resp.text
            )
    except httpx.RequestError as exc:
        logger.error("Failed to reach Notification Service: %s", exc)
