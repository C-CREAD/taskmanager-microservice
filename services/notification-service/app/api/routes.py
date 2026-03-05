"""
Notification Service API routes.

HTTP endpoints:
  POST  /notifications/internal          ← Called by Task Service (no auth header needed, internal only)
  GET   /notifications/                  ← List my notifications (paginated)
  PATCH /notifications/{id}/read         ← Mark one notification as read
  POST  /notifications/read-all          ← Mark all as read
  GET   /notifications/unread-count      ← Fast unread badge count

  POST  /devices/                        ← Register FCM device token
  DELETE /devices/{token}                ← Unregister device token

  GET   /preferences/                    ← Get my notification preferences
  PATCH /preferences/                    ← Update preferences

WebSocket:
  WS    /ws                              ← Real-time notification stream
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import func, select, update

from app.api.deps import AuthUser, DB
from app.core.jwt import get_user_id_from_token
from app.models.notification import (
    DeviceToken,
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationType,
)
from app.schemas.notification import (
    DeviceTokenRegisterRequest,
    DeviceTokenResponse,
    InternalNotificationRequest,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
)
from app.websocket.manager import manager
from app.workers.email_tasks import (
    send_due_soon_reminder_email,
    send_task_assigned_email,
    send_task_completed_email,
    send_task_created_email,
)
from app.workers.push_tasks import send_push_notification

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Notification message builders ─────────────────────────────────────────────────

_TITLES = {
    NotificationType.TASK_CREATED:   "New task created",
    NotificationType.TASK_ASSIGNED:  "Task assigned to you",
    NotificationType.TASK_COMPLETED: "Task completed 🎉",
    NotificationType.TASK_DUE_SOON:  "Task due soon ⏰",
    NotificationType.TASK_OVERDUE:   "Task overdue ⚠️",
    NotificationType.SYSTEM:         "System notification",
}


def _build_notification_text(req: InternalNotificationRequest) -> tuple[str, str]:
    title = _TITLES.get(req.type, "Notification")
    if req.type == NotificationType.TASK_CREATED:
        body = f"'{req.task_title}' has been created."
    elif req.type == NotificationType.TASK_ASSIGNED:
        body = f"'{req.task_title}' was assigned to you."
    elif req.type == NotificationType.TASK_COMPLETED:
        body = f"'{req.task_title}' has been marked as done."
    elif req.type in (NotificationType.TASK_DUE_SOON, NotificationType.TASK_OVERDUE):
        due = f" — due {req.due_date}" if req.due_date else ""
        body = f"'{req.task_title}' needs your attention{due}."
    else:
        body = "You have a new notification."
    return title, body


def _email_task_for_type(notif_type: NotificationType):
    return {
        NotificationType.TASK_CREATED:   send_task_created_email,
        NotificationType.TASK_ASSIGNED:  send_task_assigned_email,
        NotificationType.TASK_COMPLETED: send_task_completed_email,
        NotificationType.TASK_DUE_SOON:  send_due_soon_reminder_email,
    }.get(notif_type)


# ── Internal endpoint (Task Service → Notification Service) ───────────────────────

@router.post(
    "/notifications/internal",
    status_code=status.HTTP_202_ACCEPTED,
    summary="[Internal] Dispatch a notification from another service",
    include_in_schema=False,
)
async def receive_internal_notification(
    req: InternalNotificationRequest,
    db: DB,
):
    """
    Entry point for other microservices. Protected at Nginx level — not publicly reachable.
    Persists a Notification record, enqueues email/push Celery tasks, and publishes to WebSocket.
    """
    title, body = _build_notification_text(req)

    # 1. Persist notification record
    notif = Notification(
        recipient_id=req.recipient_id,
        type=req.type,
        channel=req.channel,
        title=title,
        body=body,
        data=json.dumps({"task_id": req.task_id, "task_title": req.task_title}),
    )
    db.add(notif)
    await db.flush()
    await db.refresh(notif)

    # 2. Check user preferences (best-effort — skip if not found)
    prefs_result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == req.recipient_id
        )
    )
    prefs = prefs_result.scalar_one_or_none()

    email_ok    = (prefs is None or prefs.email_enabled)    and not (prefs and prefs.is_muted(req.type))
    push_ok     = (prefs is None or prefs.push_enabled)     and not (prefs and prefs.is_muted(req.type))
    ws_ok       = (prefs is None or prefs.websocket_enabled) and not (prefs and prefs.is_muted(req.type))

    context = {
        "task_title": req.task_title,
        "due_date":   req.due_date,
        "username":   req.recipient_id,  # email task replaces this with real name
    }

    # 3. Enqueue email (Celery, async)
    if email_ok and req.channel in (NotificationChannel.EMAIL, NotificationChannel.ALL):
        email_task = _email_task_for_type(req.type)
        if email_task:
            # NOTE: In production, look up the user's email via User Service REST call
            # and pass it here. Simplified to show the pattern.
            email_task.delay(to_email=f"{req.recipient_id}@placeholder.com", context=context)

    # 4. Enqueue push (Celery, async)
    if push_ok and req.channel in (NotificationChannel.PUSH, NotificationChannel.ALL):
        send_push_notification.delay(
            user_id=req.recipient_id,
            title=title,
            body=body,
            data={"task_id": str(req.task_id), "type": req.type},
        )

    # 5. Publish to WebSocket via Redis pub/sub
    if ws_ok and req.channel in (NotificationChannel.WEBSOCKET, NotificationChannel.ALL):
        ws_payload = {
            "event":        "notification",
            "id":           str(notif.id),
            "type":         req.type,
            "title":        title,
            "body":         body,
            "task_id":      req.task_id,
            "created_at":   notif.created_at.isoformat(),
        }
        await manager.publish(req.recipient_id, ws_payload)

    # 6. Mark as sent
    notif.is_sent = True
    notif.sent_at = datetime.now(timezone.utc)
    await db.flush()

    return {"notification_id": str(notif.id), "status": "dispatched"}


# ── User-facing notification endpoints ───────────────────────────────────────────

@router.get(
    "/notifications/",
    response_model=NotificationListResponse,
    summary="List my notifications",
)
async def list_notifications(
    current_user: AuthUser,
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
):
    base_q = select(Notification).where(
        Notification.recipient_id == current_user.id
    )
    if unread_only:
        base_q = base_q.where(Notification.is_read == False)

    # Total count
    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Unread count
    unread_q = select(func.count()).where(
        Notification.recipient_id == current_user.id,
        Notification.is_read == False,
    )
    unread = (await db.execute(unread_q)).scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    results_q = base_q.order_by(Notification.created_at.desc()).offset(offset).limit(page_size)
    notifications = (await db.execute(results_q)).scalars().all()

    return NotificationListResponse(
        count=total,
        unread_count=unread,
        results=[NotificationResponse.model_validate(n) for n in notifications],
    )


@router.get(
    "/notifications/unread-count",
    summary="Get unread notification count (for badge UI)",
)
async def unread_count(current_user: AuthUser, db: DB):
    q = select(func.count()).where(
        Notification.recipient_id == current_user.id,
        Notification.is_read == False,
    )
    count = (await db.execute(q)).scalar_one()
    return {"unread_count": count}


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_read(notification_id: str, current_user: AuthUser, db: DB):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.is_read = True
    await db.flush()
    await db.refresh(notif)
    return notif


@router.post(
    "/notifications/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
)
async def mark_all_read(current_user: AuthUser, db: DB):
    await db.execute(
        update(Notification)
        .where(
            Notification.recipient_id == current_user.id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )


# ── Device token endpoints ────────────────────────────────────────────────────────

@router.post(
    "/devices/",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a FCM device token for push notifications",
)
async def register_device(
    payload: DeviceTokenRegisterRequest,
    current_user: AuthUser,
    db: DB,
):
    # Upsert: update if token already exists
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.token == payload.token)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.user_id = current_user.id
        existing.device_name = payload.device_name
        existing.is_active = True
        existing.last_used_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(existing)
        return existing

    device = DeviceToken(
        user_id=current_user.id,
        token=payload.token,
        device_name=payload.device_name,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)
    return device


@router.delete(
    "/devices/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister a device token",
)
async def unregister_device(token: str, current_user: AuthUser, db: DB):
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.token == token,
            DeviceToken.user_id == current_user.id,
        )
    )
    device = result.scalar_one_or_none()
    if device:
        device.is_active = False
        await db.flush()


# ── Preference endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/preferences/",
    response_model=NotificationPreferenceResponse,
    summary="Get my notification preferences",
)
async def get_preferences(current_user: AuthUser, db: DB):
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Return defaults if not yet configured
        return NotificationPreferenceResponse(
            user_id=current_user.id,
            email_enabled=True,
            push_enabled=True,
            websocket_enabled=True,
            muted_types=[],
            updated_at=datetime.now(timezone.utc),
        )

    return NotificationPreferenceResponse.from_orm_with_types(prefs)


@router.patch(
    "/preferences/",
    response_model=NotificationPreferenceResponse,
    summary="Update my notification preferences",
)
async def update_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: AuthUser,
    db: DB,
):
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)

    if payload.email_enabled is not None:
        prefs.email_enabled = payload.email_enabled
    if payload.push_enabled is not None:
        prefs.push_enabled = payload.push_enabled
    if payload.websocket_enabled is not None:
        prefs.websocket_enabled = payload.websocket_enabled
    if payload.muted_types is not None:
        prefs.muted_types = ",".join(payload.muted_types)

    prefs.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(prefs)
    return NotificationPreferenceResponse.from_orm_with_types(prefs)


# ── WebSocket endpoint ────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.

    Connection flow:
      1. Client connects: ws://host/api/ws
      2. Client sends: {"token": "<JWT access token>"}
      3. Server authenticates and starts streaming notifications

    Client receives JSON frames:
      {"event": "connected", "user_id": "..."}
      {"event": "notification", "id": "...", "type": "...", "title": "...", "body": "..."}
      {"event": "ping"}   ← keepalive every 30s

    Client sends:
      {"action": "ping"}  ← optional keepalive from client side
    """
    await websocket.accept()

    # Step 1: Wait for auth frame
    try:
        auth_frame = await websocket.receive_json()
        token = auth_frame.get("token", "")
        user_id = get_user_id_from_token(token)
    except (JWTError, Exception) as exc:
        await websocket.send_json({"event": "error", "detail": "Authentication failed."})
        await websocket.close(code=4001)
        return

    # Step 2: Register connection
    # Re-accept is not needed — we already accepted above; manager.connect skips re-accept
    _connections_registered = False
    from app.websocket.manager import _connections
    _connections[user_id].add(websocket)
    _connections_registered = True

    await websocket.send_json({
        "event": "connected",
        "user_id": user_id,
        "message": "Real-time notifications active.",
    })
    logger.info("WS authenticated: user=%s", user_id)

    # Step 3: Keep connection alive, handle client messages
    try:
        import asyncio
        async def keepalive():
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({"event": "ping"})
                except Exception:
                    break

        keepalive_task = asyncio.create_task(keepalive())

        while True:
            try:
                data = await websocket.receive_json()
                if data.get("action") == "ping":
                    await websocket.send_json({"event": "pong"})
            except WebSocketDisconnect:
                break
            except Exception:
                break

        keepalive_task.cancel()

    finally:
        if _connections_registered:
            _connections[user_id].discard(websocket)
            if not _connections[user_id]:
                del _connections[user_id]
        logger.info("WS disconnected: user=%s", user_id)
