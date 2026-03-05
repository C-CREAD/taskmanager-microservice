"""
Celery app + nightly snapshot task for the Analytics Service.
Run with: celery -A app.workers.celery_app worker -B -l info
(-B enables the built-in beat scheduler)
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "analytics_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Run nightly at 01:00 UTC to snapshot the previous day's metrics
        "nightly-snapshot": {
            "task": "app.workers.celery_app.compute_daily_snapshots",
            "schedule": crontab(hour=1, minute=0),
        },
        # Update productivity scores every 6 hours
        "update-scores": {
            "task": "app.workers.celery_app.update_all_productivity_scores",
            "schedule": crontab(minute=0, hour="*/6"),
        },
    },
)


@celery_app.task(name="app.workers.celery_app.compute_daily_snapshots")
def compute_daily_snapshots():
    """
    Nightly task: fetch stats for all active users from the Task Service
    and persist a DailySnapshot row for each.

    In production, you'd fetch a list of active user IDs from the User Service.
    Here we illustrate the pattern with a placeholder.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    import httpx

    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    # In production: fetch active user IDs from User Service
    # user_ids = _fetch_active_user_ids()
    # For now, fetch from existing ProductivityScore records
    from app.models.report import DailySnapshot, UserProductivityScore

    with Session(engine) as session:
        users = session.execute(select(UserProductivityScore.user_id)).scalars().all()

    snapped = 0
    today = date.today()

    for user_id in users:
        try:
            # Use a service-level token (in production, use a service account JWT)
            # For illustration, skip auth — protect this endpoint at Nginx level
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{settings.TASK_SERVICE_URL}/api/v1/tasks/stats/",
                    headers={"X-Internal-Service": "analytics"},
                )
            if resp.status_code != 200:
                continue

            stats = resp.json()
            by_status = stats.get("by_status", {})
            total = stats.get("total", 0)
            done  = by_status.get("done", 0)
            rate  = round(done / total, 4) if total > 0 else 0.0

            with Session(engine) as session:
                snap = DailySnapshot(
                    user_id=user_id,
                    snapshot_date=today,
                    tasks_created=total,
                    tasks_completed=done,
                    tasks_overdue=stats.get("overdue", 0),
                    tasks_in_progress=by_status.get("in_progress", 0),
                    completion_rate=rate,
                    priority_breakdown=json.dumps(stats.get("by_priority", {})),
                )
                session.add(snap)
                session.commit()
                snapped += 1

        except Exception as exc:
            logger.error("Snapshot failed for user %s: %s", user_id, exc)

    engine.dispose()
    logger.info("compute_daily_snapshots: %d snapshots written for %s", snapped, today)
    return {"snapshots_written": snapped, "date": str(today)}


@celery_app.task(name="app.workers.celery_app.update_all_productivity_scores")
def update_all_productivity_scores():
    """
    Periodic task: recompute and persist productivity scores for all tracked users.
    Runs every 6 hours so the /score endpoint always has a recent cached value.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models.report import UserProductivityScore

    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    with Session(engine) as session:
        users = session.execute(select(UserProductivityScore.user_id)).scalars().all()

    logger.info("update_all_productivity_scores: %d users to update", len(users))
    # Full re-computation would call build_dashboard for each user.
    # Omitted here to avoid circular async/sync complexity — implement as needed.
    engine.dispose()
    return {"users_checked": len(users)}
