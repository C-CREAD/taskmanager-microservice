"""
Celery tasks for email delivery.
Uses aiosmtplib for async SMTP + Jinja2 for HTML templates.
Each task is idempotent — safe to retry on failure.
"""
from __future__ import annotations

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Jinja2 template environment
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _render_template(template_name: str, context: dict) -> tuple[str, str]:
    """Render an HTML email template and generate a plain-text fallback."""
    tmpl = _jinja_env.get_template(template_name)
    html = tmpl.render(**context)
    # Simple plain-text: strip tags (good enough for fallback)
    import re
    text = re.sub(r"<[^>]+>", "", html).strip()
    return html, text


async def _send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    """Low-level async SMTP send."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=False,
        start_tls=settings.SMTP_USE_TLS,
    )


# ── Celery tasks ──────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.workers.email_tasks.send_task_created_email",
    max_retries=3,
    default_retry_delay=30,
    queue="email",
)
def send_task_created_email(self, to_email: str, context: dict) -> dict:
    """
    Send a 'Task Created' confirmation email.
    context keys: task_title, due_date (optional), username
    """
    try:
        html, text = _render_template("task_created.html", context)
        asyncio.get_event_loop().run_until_complete(
            _send_email(
                to_email=to_email,
                subject=f"✅ New task: {context.get('task_title', 'Untitled')}",
                html_body=html,
                text_body=text,
            )
        )
        logger.info("task_created email sent to %s", to_email)
        return {"status": "sent", "to": to_email}
    except Exception as exc:
        logger.error("Failed to send task_created email to %s: %s", to_email, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.workers.email_tasks.send_task_assigned_email",
    max_retries=3,
    default_retry_delay=30,
    queue="email",
)
def send_task_assigned_email(self, to_email: str, context: dict) -> dict:
    """
    Send a 'Task Assigned' notification email.
    context keys: task_title, assigned_by_username, due_date (optional)
    """
    try:
        html, text = _render_template("task_assigned.html", context)
        asyncio.get_event_loop().run_until_complete(
            _send_email(
                to_email=to_email,
                subject=f"📋 Task assigned to you: {context.get('task_title', 'Untitled')}",
                html_body=html,
                text_body=text,
            )
        )
        logger.info("task_assigned email sent to %s", to_email)
        return {"status": "sent", "to": to_email}
    except Exception as exc:
        logger.error("Failed to send task_assigned email to %s: %s", to_email, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.workers.email_tasks.send_due_soon_reminder_email",
    max_retries=3,
    default_retry_delay=60,
    queue="email",
)
def send_due_soon_reminder_email(self, to_email: str, context: dict) -> dict:
    """
    Send a 'Task Due Soon' reminder email.
    context keys: task_title, due_date, username
    """
    try:
        html, text = _render_template("task_due_soon.html", context)
        asyncio.get_event_loop().run_until_complete(
            _send_email(
                to_email=to_email,
                subject=f"⏰ Reminder: '{context.get('task_title')}' is due soon",
                html_body=html,
                text_body=text,
            )
        )
        logger.info("due_soon email sent to %s", to_email)
        return {"status": "sent", "to": to_email}
    except Exception as exc:
        logger.error("Failed to send due_soon email to %s: %s", to_email, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.workers.email_tasks.send_task_completed_email",
    max_retries=2,
    default_retry_delay=30,
    queue="email",
)
def send_task_completed_email(self, to_email: str, context: dict) -> dict:
    """context keys: task_title, username"""
    try:
        html, text = _render_template("task_completed.html", context)
        asyncio.get_event_loop().run_until_complete(
            _send_email(
                to_email=to_email,
                subject=f"🎉 Task completed: {context.get('task_title', 'Untitled')}",
                html_body=html,
                text_body=text,
            )
        )
        logger.info("task_completed email sent to %s", to_email)
        return {"status": "sent", "to": to_email}
    except Exception as exc:
        logger.error("Failed to send task_completed email to %s: %s", to_email, exc)
        raise self.retry(exc=exc)
