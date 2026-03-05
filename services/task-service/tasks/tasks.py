"""
Celery tasks for the Task Service.
The beat scheduler runs check_due_date_reminders periodically.
"""
from __future__ import annotations

import logging

import httpx
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_due_date_reminders(self):
    """
    Periodic task — run every 15 minutes via Celery Beat.
    Finds tasks due within the next hour that haven't had a reminder sent,
    and fires a notification for each one.
    """
    from .models import Task  # local import to avoid app-loading issues

    now = timezone.now()
    one_hour_from_now = now + timezone.timedelta(hours=1)

    upcoming = Task.objects.filter(
        due_date__gte=now,
        due_date__lte=one_hour_from_now,
        reminder_sent=False,
        status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW],
    ).select_related("category")

    count = 0
    for task in upcoming:
        try:
            _send_reminder(task)
            task.reminder_sent = True
            task.save(update_fields=["reminder_sent"])
            count += 1
        except Exception as exc:
            logger.error("Failed to send reminder for task %s: %s", task.id, exc)

    logger.info("check_due_date_reminders: sent %d reminders.", count)
    return {"reminders_sent": count}


def _send_reminder(task) -> None:
    """Call the Notification Service to dispatch the reminder."""
    url = f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/internal"
    payload = {
        "type": "task_due_soon",
        "recipient_id": task.owner_id,
        "task_id": task.id,
        "task_title": task.title,
        "due_date": task.due_date.isoformat(),
    }
    with httpx.Client(timeout=3.0) as client:
        resp = client.post(url, json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"Notification Service error {resp.status_code}: {resp.text}")


@shared_task
def mark_overdue_tasks():
    """
    Optional — run daily. Logs overdue tasks for analytics purposes.
    Could also push them to a separate status or trigger escalation.
    """
    from .models import Task

    now = timezone.now()
    overdue = Task.objects.filter(
        due_date__lt=now,
        status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW],
        reminder_sent=True,
    )
    ids = list(overdue.values_list("id", flat=True))
    logger.info("mark_overdue_tasks: %d overdue tasks found: %s", len(ids), ids)
    return {"overdue_count": len(ids), "task_ids": ids}
