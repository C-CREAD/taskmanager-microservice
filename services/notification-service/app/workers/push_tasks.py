"""
Celery tasks for push notification delivery via Firebase Cloud Messaging (FCM).
Tokens are stored in DeviceToken table; invalid tokens are deactivated automatically.
"""
from __future__ import annotations

import logging

from app.workers.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _get_firebase():
    """Lazy-initialise Firebase Admin SDK."""
    global _firebase_initialized
    if not _firebase_initialized and settings.FIREBASE_CREDENTIALS_PATH:
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
    from firebase_admin import messaging
    return messaging


@celery_app.task(
    bind=True,
    name="app.workers.push_tasks.send_push_notification",
    max_retries=3,
    default_retry_delay=15,
    queue="push",
)
def send_push_notification(
    self,
    user_id: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> dict:
    """
    Send a push notification to all active device tokens for a user.
    Deactivates tokens that are reported invalid by FCM.
    """
    # Import here to allow task registration even if firebase isn't configured
    from sqlalchemy import create_engine, select, update
    from sqlalchemy.orm import Session

    # Use sync engine for Celery worker context
    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")

    try:
        messaging = _get_firebase()
    except Exception as exc:
        logger.warning("Firebase not configured, skipping push: %s", exc)
        return {"status": "skipped", "reason": "firebase_not_configured"}

    engine = create_engine(sync_db_url)

    try:
        # Avoid circular import at module level
        from app.models.notification import DeviceToken

        with Session(engine) as session:
            tokens = session.execute(
                select(DeviceToken).where(
                    DeviceToken.user_id == user_id,
                    DeviceToken.is_active == True,
                )
            ).scalars().all()

            if not tokens:
                logger.info("No active device tokens for user %s", user_id)
                return {"status": "no_tokens", "user_id": user_id}

            results = {"sent": 0, "failed": 0, "deactivated": []}

            for device in tokens:
                try:
                    message = messaging.Message(
                        notification=messaging.Notification(title=title, body=body),
                        data={k: str(v) for k, v in (data or {}).items()},
                        token=device.token,
                    )
                    messaging.send(message)
                    results["sent"] += 1
                    logger.info("Push sent to device %s (user=%s)", device.id, user_id)

                except messaging.UnregisteredError:
                    # Token is no longer valid — deactivate it
                    session.execute(
                        update(DeviceToken)
                        .where(DeviceToken.id == device.id)
                        .values(is_active=False)
                    )
                    results["deactivated"].append(str(device.id))
                    logger.warning("Deactivated stale FCM token %s", device.token[:20])

                except Exception as exc:
                    results["failed"] += 1
                    logger.error("Push failed for device %s: %s", device.id, exc)

            session.commit()
            return results

    except Exception as exc:
        logger.error("Push task failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc)
    finally:
        engine.dispose()
